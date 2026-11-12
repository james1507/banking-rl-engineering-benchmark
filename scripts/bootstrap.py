"""Create only local, ignored secrets. Compatible with macOS system Python."""

import secrets
from pathlib import Path

path = Path(".env")
values = {}
if path.exists():
    values = dict(
        line.split("=", 1)
        for line in path.read_text().splitlines()
        if "=" in line and not line.startswith("#")
    )
for key in ("POSTGRES_PASSWORD", "APP_DB_PASSWORD", "JWT_SECRET", "DEMO_PASSWORD"):
    if not values.get(key):
        values[key] = secrets.token_hex(32)
values.setdefault("API_PORT", "8010")
values.setdefault("DB_PORT", "5440")
path.write_text("".join(key + "=" + value + "\n" for key, value in values.items()))
path.chmod(0o600)
print("Local secrets ready in .env; demo password stays there.")
