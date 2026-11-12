"""Create unique disposable test DB, migrate, run checks, always drop only that DB."""

import os
import subprocess
import sys
from uuid import uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from banking_lab.infrastructure.db import require_local


def main() -> None:
    admin = os.environ["ADMIN_DATABASE_URL"]
    require_local(admin)
    name = "lab_test_" + uuid4().hex
    owner_url = make_url(admin).set(database=name)
    app_url = make_url(os.environ["DATABASE_URL"]).set(database=name)
    require_local(str(owner_url), disposable=True)
    control = create_engine(admin, isolation_level="AUTOCOMMIT")
    with control.connect() as c:
        c.execute(text(f'CREATE DATABASE "{name}"'))
    env = {
        **os.environ,
        "DATABASE_URL": owner_url.render_as_string(hide_password=False),
        "APP_ENV": "test",
    }
    try:
        subprocess.run(["alembic", "upgrade", "head"], env=env, check=True)
        env.update(
            DATABASE_URL=app_url.render_as_string(hide_password=False),
            TEST_OWNER_URL=owner_url.render_as_string(hide_password=False),
        )
        result = subprocess.run([sys.executable, "-m", "pytest", *sys.argv[1:]], env=env)
        sys.exit(result.returncode)
    finally:
        with control.connect() as c:
            c.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
        control.dispose()


if __name__ == "__main__":
    main()
