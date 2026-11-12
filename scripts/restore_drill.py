"""Pause this local demo, restore synthetic logical backup into NEW disposable DB, verify."""

import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
DC = ["docker", "compose"]


def run(args, **kwargs):
    return subprocess.run(DC + args, cwd=ROOT, check=True, capture_output=True, **kwargs).stdout


def main():
    name = "lab_test_restore_" + uuid4().hex[:12]
    assert name.startswith("lab_test_restore_") and name.replace("_", "").isalnum()
    target = ROOT / "artifacts/backup"
    target.mkdir(parents=True, exist_ok=True)
    dump = target / "synthetic.dump"
    running = run(["ps", "--status", "running", "--services"]).decode().splitlines()
    paused = [service for service in ("api", "worker") if service in running]
    started = datetime.now(timezone.utc).isoformat()
    timer = time.monotonic()
    stats_sql = """SELECT jsonb_build_object('transfers',(SELECT count(*) FROM transfers),'postings',(SELECT count(*) FROM ledger_postings),'ledger_hash',(SELECT md5(string_agg(id::text||journal_group_id::text||account_id::text||signed_amount_minor::text,',' ORDER BY id)) FROM ledger_postings),'replay_hash',(SELECT md5(string_agg(id::text||request_hash||response_body::text,',' ORDER BY id)) FROM idempotency_records));"""

    def stats(database):
        return json.loads(
            run(
                [
                    "exec",
                    "-T",
                    "db",
                    "psql",
                    "-U",
                    "lab_owner",
                    "-d",
                    database,
                    "-At",
                    "-c",
                    stats_sql,
                ]
            )
        )

    try:
        if paused:
            run(["stop", *paused])
        before = stats("banking_lab")
        with dump.open("wb") as output:
            os.chmod(dump, 0o600)
            subprocess.run(
                DC
                + [
                    "exec",
                    "-T",
                    "db",
                    "pg_dump",
                    "-U",
                    "lab_owner",
                    "-d",
                    "banking_lab",
                    "-Fc",
                    "--no-owner",
                ],
                cwd=ROOT,
                stdout=output,
                check=True,
            )
        run(
            [
                "exec",
                "-T",
                "db",
                "psql",
                "-U",
                "lab_owner",
                "-d",
                "banking_lab",
                "-v",
                "ON_ERROR_STOP=1",
                "-c",
                f'CREATE DATABASE "{name}"',
            ]
        )
        with dump.open("rb") as data:
            subprocess.run(
                DC
                + [
                    "exec",
                    "-T",
                    "db",
                    "pg_restore",
                    "-U",
                    "lab_owner",
                    "-d",
                    name,
                    "--no-owner",
                    "--exit-on-error",
                ],
                cwd=ROOT,
                stdin=data,
                check=True,
            )
        after = stats(name)
        if before != after:
            raise AssertionError("Restore counts/digests differ")
        code = (
            "import os,json; from sqlalchemy.engine import make_url; from banking_lab.infrastructure.db import build_engine,require_local; from banking_lab.application.reconciliation import reconcile; url=make_url(os.environ['DATABASE_URL']).set(database='"
            + name
            + "').render_as_string(hide_password=False); require_local(url,disposable=True); report=reconcile(build_engine(url)); print(json.dumps(report)); raise SystemExit(0 if report['status']=='PASS' else 1)"
        )
        reconciliation = json.loads(run(["run", "--rm", "-T", "tools", "-c", code]))
        report = {
            "status": "PASS",
            "started_at": started,
            "ended_at": datetime.now(timezone.utc).isoformat(),
            "duration_ms": round((time.monotonic() - timer) * 1000),
            "source": "banking_lab (local synthetic)",
            "target": name,
            "source_stats": before,
            "restored_stats": after,
            "reconciliation": reconciliation,
            "limitations": "One local logical-backup drill; no measured production RPO/RTO or PITR/HA claim",
        }
        (target / "result.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2))
    finally:
        run(
            [
                "exec",
                "-T",
                "db",
                "psql",
                "-U",
                "lab_owner",
                "-d",
                "banking_lab",
                "-c",
                f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)',
            ]
        )
        if paused:
            run(["--profile", "worker", "up", "-d", "--wait", *paused])


if __name__ == "__main__":
    main()
