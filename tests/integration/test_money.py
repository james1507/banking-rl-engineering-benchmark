import json
import os
import subprocess
import sys
from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from banking_lab.application.history import HistoryService
from banking_lab.application.reconciliation import reconcile
from banking_lab.application.transfers import TransferService
from banking_lab.domain.rules import DomainError, TransferCommand


def command(f, amount=12500):
    return TransferCommand(f["alice_account"], f["bob_account"], amount)


def test_transfer_and_durable_replay(db, fixture):
    svc = TransferService(db[0])
    cmd = command(fixture)
    first = svc.create(fixture["alice"], cmd, "transfer-0001", "first-request")
    again = TransferService(db[0]).create(fixture["alice"], cmd, "transfer-0001", "new-request")
    assert first.status == 201 and again.replayed and again.body == first.body
    with pytest.raises(DomainError, match="IDEMPOTENCY_KEY_REUSED"):
        svc.create(fixture["alice"], replace(cmd, amount_minor=1), "transfer-0001", "conflict")
    assert reconcile(db[0])["invariant_violations"] == 0


def test_persisted_rejection(db, fixture):
    svc = TransferService(db[0])
    cmd = command(fixture, 100001)
    first = svc.create(fixture["alice"], cmd, "reject-key-0001", "first")
    assert first.status == 409 and first.body["error"]["code"] == "INSUFFICIENT_FUNDS"
    svc.create(
        fixture["bob"],
        TransferCommand(fixture["bob_account"], fixture["alice_account"], 100),
        "fund-extra-0001",
        "fund",
    )
    assert svc.create(fixture["alice"], cmd, "reject-key-0001", "second").body == first.body
    assert reconcile(db[0])["status"] == "PASS"


@pytest.mark.parametrize(
    "status,expected", [("FROZEN", "ACCOUNT_FROZEN"), ("CLOSED", "ACCOUNT_CLOSED")]
)
def test_status_and_ownership(db, fixture, status, expected):
    with db[1].begin() as c:
        c.execute(
            text("UPDATE accounts SET status=:status WHERE id=:id"),
            {"status": status, "id": fixture["bob_account"]},
        )
    svc = TransferService(db[0])
    result = svc.create(fixture["alice"], command(fixture), "status-key-0001", "status")
    assert result.body["error"]["code"] == expected
    with pytest.raises(DomainError, match="RESOURCE_NOT_FOUND"):
        svc.create(fixture["bob"], command(fixture), "owner-key-0001", "owner")
    assert reconcile(db[0])["status"] == "PASS"


@pytest.mark.parametrize(
    "point", ["BEFORE_POSTING", "AFTER_SOURCE_UPDATE", "BEFORE_LEDGER_INSERT", "BEFORE_SQL_COMMIT"]
)
def test_exception_rollback(db, fixture, point):
    def fault(here):
        if point == here:
            raise RuntimeError("controlled fault")

    before = reconcile(db[0])["counts"]
    with pytest.raises(RuntimeError):
        TransferService(db[0], fault=fault).create(
            fixture["alice"], command(fixture), "rollback-key-0001", "rollback"
        )
    assert reconcile(db[0])["counts"] == before
    assert (
        TransferService(db[0])
        .create(fixture["alice"], command(fixture), "rollback-key-0001", "retry")
        .status
        == 201
    )
    assert reconcile(db[0])["status"] == "PASS"


@pytest.mark.parametrize(
    "point",
    [
        "BEFORE_POSTING",
        "AFTER_SOURCE_UPDATE",
        "BEFORE_SQL_COMMIT",
        "AFTER_SQL_COMMIT_BEFORE_HTTP_RESPONSE",
    ],
)
def test_process_kill(db, fixture, point):
    before = reconcile(db[0])["counts"]["transfers"]
    args = [
        sys.executable,
        "-m",
        "banking_lab.cli",
        "submit",
        "--actor",
        str(fixture["alice"]),
        "--source",
        str(fixture["alice_account"]),
        "--destination",
        str(fixture["bob_account"]),
        "--key",
        "crash-key-0001",
    ]
    child = subprocess.run(
        args, env={**os.environ, "FAULT_POINT": point}, capture_output=True, text=True, timeout=20
    )
    assert child.returncode == 86, child.stderr
    committed = point == "AFTER_SQL_COMMIT_BEFORE_HTTP_RESPONSE"
    assert reconcile(db[0])["counts"]["transfers"] == before + int(committed)
    retry = subprocess.run(
        args,
        env={k: v for k, v in os.environ.items() if k != "FAULT_POINT"},
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert retry.returncode == 0, retry.stderr
    assert json.loads(retry.stdout)["status"] == 201
    report = reconcile(db[0])
    assert report["status"] == "PASS" and report["counts"]["transfers"] == before + 1


def test_database_guards_and_drift_detector(db, fixture):
    for sql in (
        "UPDATE ledger_postings SET signed_amount_minor=1",
        "UPDATE accounts SET balance_minor=balance_minor+1",
    ):
        with pytest.raises(DBAPIError):
            with db[0].begin() as c:
                c.execute(text(sql))
    with db[1].begin() as c:
        c.execute(text("SET LOCAL session_replication_role=replica"))
        c.execute(
            text("UPDATE accounts SET balance_minor=balance_minor+1 WHERE id=:id"),
            {"id": fixture["alice_account"]},
        )
    report = reconcile(db[0])
    print(json.dumps(report))
    assert "BALANCE_DRIFT" in {x["code"] for x in report["findings"]}


def test_equal_timestamp_pages_and_tamper(db, fixture):
    def clock():
        return datetime(2026, 1, 1, tzinfo=UTC)

    for n in range(23):
        TransferService(db[0], clock=clock).create(
            fixture["alice"], command(fixture, 1), f"page-key-{n:04}", "page"
        )
    svc = HistoryService(db[0], "cursor-secret")
    ids = []
    cursor = None
    while True:
        page = svc.page(fixture["alice"], account=fixture["alice_account"], limit=5, cursor=cursor)
        ids.extend(str(x["id"]) for x in page["items"])
        cursor = page["next_cursor"]
        if not page["has_more"]:
            break
    assert len(ids) == len(set(ids)) == 24
    page = svc.page(fixture["alice"], account=fixture["alice_account"], limit=5)
    with pytest.raises(DomainError):
        svc.page(fixture["alice"], account=fixture["alice_savings"], cursor=page["next_cursor"])
    with pytest.raises(DomainError):
        svc.page(fixture["alice"], cursor=page["next_cursor"] + "bad")


@settings(
    max_examples=12, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(st.lists(st.integers(min_value=1, max_value=10000), min_size=1, max_size=8))
def test_transfer_sequences_preserve_all_invariants(db, fixture, amounts):
    for amount in amounts:
        svc = TransferService(db[0])
        key = str(uuid4())
        first = svc.create(fixture["alice"], command(fixture, amount), key, "property")
        assert (
            svc.create(fixture["alice"], command(fixture, amount), key, "replay").body == first.body
        )
        assert reconcile(db[0])["status"] == "PASS"
