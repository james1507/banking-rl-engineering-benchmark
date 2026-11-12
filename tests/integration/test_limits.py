from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier

from banking_lab.application.operations import configure_limit
from banking_lab.application.reconciliation import reconcile
from banking_lab.application.transfers import TransferService
from banking_lab.domain.rules import TransferCommand


def test_account_limit_and_replay_at_utc_boundary(db, fixture):
    configure_limit(
        db[0], fixture["admin"], "ACCOUNT", fixture["alice_account"], 100, "limit-config"
    )
    now = [datetime(2026, 2, 1, 23, 59, 59, tzinfo=UTC)]
    service = TransferService(db[0], clock=lambda: now[0])
    cmd = TransferCommand(fixture["alice_account"], fixture["bob_account"], 70)
    first = service.create(fixture["alice"], cmd, "utc-limit-0001", "limit")
    assert first.status == 201
    rejected = service.create(fixture["alice"], cmd, "utc-limit-0002", "limit")
    assert rejected.body["error"]["code"] == "TRANSFER_LIMIT_EXCEEDED"
    now[0] += timedelta(seconds=1)
    assert service.create(fixture["alice"], cmd, "utc-limit-0001", "replay").body == first.body
    assert service.create(fixture["alice"], cmd, "utc-limit-0002", "replay").body == rejected.body
    assert service.create(fixture["alice"], cmd, "utc-limit-0003", "new-day").status == 201
    assert reconcile(db[0], checked_at=now[0])["status"] == "PASS"


def test_user_limit_two_accounts_concurrently(db, fixture):
    configure_limit(db[0], fixture["admin"], "USER", fixture["alice"], 100, "user-limit")
    barrier = Barrier(2)

    def clock():
        return datetime(2026, 2, 2, 10, tzinfo=UTC)

    def send(n):
        barrier.wait(timeout=5)
        source = fixture["alice_account"] if n == 0 else fixture["alice_savings"]
        return TransferService(db[0], clock=clock).create(
            fixture["alice"],
            TransferCommand(source, fixture["bob_account"], 70),
            f"user-limit-{n}",
            "user-limit",
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(send, range(2)))
    assert sorted(r.status for r in results) == [201, 409]
    assert reconcile(db[0], checked_at=clock())["status"] == "PASS"
