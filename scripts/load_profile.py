"""Controlled HTTP and history profile in a fresh disposable database."""

import concurrent.futures
import json
import math
import os
import platform
import secrets
import statistics
import subprocess
import sys
import time
from pathlib import Path
from uuid import UUID, uuid4

import httpx
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from banking_lab.application.reconciliation import reconcile
from banking_lab.application.seed import seed
from banking_lab.application.transfers import TransferService
from banking_lab.domain.rules import TransferCommand
from banking_lab.infrastructure.db import build_engine, require_local


def main():
    admin = os.environ["ADMIN_DATABASE_URL"]
    require_local(admin)
    name = "lab_test_load_" + uuid4().hex[:12]
    owner_url = make_url(admin).set(database=name)
    app_url = make_url(os.environ["DATABASE_URL"]).set(database=name)
    control = create_engine(admin, isolation_level="AUTOCOMMIT")
    with control.connect() as c:
        c.execute(text(f'CREATE DATABASE "{name}"'))
    target = Path("artifacts/load")
    target.mkdir(parents=True, exist_ok=True)
    server = None
    db = None
    started = time.monotonic()
    try:
        env = {
            **os.environ,
            "DATABASE_URL": owner_url.render_as_string(hide_password=False),
            "APP_ENV": "test",
        }
        subprocess.run(["alembic", "upgrade", "head"], env=env, check=True)
        db = build_engine(app_url.render_as_string(hide_password=False))
        password = secrets.token_urlsafe(24)
        ids = {k: UUID(v) for k, v in seed(db, password).items()}
        env["DATABASE_URL"] = app_url.render_as_string(hide_password=False)
        with (target / "api.log").open("w") as log:
            server = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "banking_lab.main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "8001",
                    "--no-access-log",
                ],
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
            with httpx.Client(base_url="http://127.0.0.1:8001", timeout=15, verify=False) as client:
                deadline = time.monotonic() + 20
                while True:
                    try:
                        if client.get("/health/ready").status_code == 200:
                            break
                    except httpx.TransportError:
                        pass
                    if time.monotonic() > deadline:
                        raise RuntimeError("Load API failed readiness")
                    time.sleep(0.1)
                login = client.post(
                    "/api/v1/auth/login", json={"email": "alice@example.test", "password": password}
                )
                login.raise_for_status()
                authorization = "Bearer " + login.json()["access_token"]
                payload = {
                    "source_account_id": str(ids["alice_account"]),
                    "destination_account_id": str(ids["bob_account"]),
                    "amount_minor": 1,
                    "currency": "USD",
                }

                def send(_):
                    before = time.monotonic()
                    response = client.post(
                        "/api/v1/transfers",
                        headers={"Authorization": authorization, "Idempotency-Key": str(uuid4())},
                        json=payload,
                    )
                    if response.status_code != 201:
                        raise AssertionError(
                            "Load transfer failed with " + str(response.status_code)
                        )
                    return (time.monotonic() - before) * 1000

                for n in range(10):
                    send(n)
                samples = []
                for sample in range(3):
                    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
                        timings = sorted(pool.map(send, range(50)))
                    samples.append(
                        {
                            "sample": sample + 1,
                            "requests": 50,
                            "median_ms": statistics.median(timings),
                            "p95_ms": timings[math.ceil(len(timings) * 0.95) - 1],
                            "max_ms": max(timings),
                        }
                    )
        service = TransferService(db)
        command = TransferCommand(ids["alice_account"], ids["bob_account"], 1)
        for n in range(1000):
            assert (
                service.create(
                    ids["alice"], command, "history-load-" + str(n), "load-history"
                ).status
                == 201
            )
        with db.connect() as c:
            plan = c.execute(
                text(
                    "EXPLAIN (ANALYZE,BUFFERS,FORMAT JSON) SELECT id,journal_group_id,signed_amount_minor,created_at FROM ledger_postings WHERE account_id=:id ORDER BY created_at DESC,id DESC LIMIT 20"
                ),
                {"id": ids["alice_account"]},
            ).scalar_one()
            pg = c.execute(text("SELECT version()")).scalar_one()
        (target / "history-explain-before-analyze.json").write_text(
            json.dumps(plan, indent=2) + "\n"
        )
        owner = create_engine(owner_url)
        with owner.begin() as c:
            c.execute(text("ANALYZE ledger_postings"))
        owner.dispose()
        with db.connect() as c:
            plan = c.execute(
                text(
                    "EXPLAIN (ANALYZE,BUFFERS,FORMAT JSON) SELECT id,journal_group_id,signed_amount_minor,created_at FROM ledger_postings WHERE account_id=:id ORDER BY created_at DESC,id DESC LIMIT 20"
                ),
                {"id": ids["alice_account"]},
            ).scalar_one()
        (target / "history-explain.json").write_text(json.dumps(plan, indent=2) + "\n")
        # Drain synthetic notifications before lag analysis; no network service involved.
        from banking_lab.infrastructure.worker import OutboxWorker

        worker = OutboxWorker(db)
        while worker.tick():
            pass
        invariant = reconcile(db)
        if invariant["status"] != "PASS":
            raise AssertionError("Load broke accounting invariants")
        report = {
            "status": "PASS",
            "profile": {
                "platform": platform.platform(),
                "python": platform.python_version(),
                "postgres": pg,
                "concurrency": 10,
                "warmup_requests": 10,
                "samples": 3,
                "requests_per_sample": 50,
                "history_transfers": 1000,
                "seed": "deterministic demo IDs, random request keys",
                "scope": "local container simulation, not production SLO",
            },
            "samples": samples,
            "invariants": invariant,
            "duration_ms": round((time.monotonic() - started) * 1000),
        }
        (target / "result.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2))
    finally:
        if server:
            server.terminate()
            server.wait(timeout=15)
        if db:
            db.dispose()
        with control.connect() as c:
            c.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
        control.dispose()


if __name__ == "__main__":
    main()
