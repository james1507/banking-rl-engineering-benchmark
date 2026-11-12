from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest
from sqlalchemy import text

from banking_lab.application.reconciliation import reconcile
from banking_lab.application.transfers import utc_now
from banking_lab.infrastructure.worker import FakeProvider, OutboxWorker


def count(db, table):
    with db.connect() as c:
        return c.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()


def test_two_workers_single_effect(db, fixture):
    def tick(_):
        return OutboxWorker(db[0]).tick()

    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(tick, range(12)))
    assert count(db[0], "notification_effects") == count(db[0], "outbox_events") == 3
    assert count(db[0], "inbox_receipts") == 3
    assert reconcile(db[0])["status"] == "PASS"


@pytest.mark.parametrize("mode", ["500", "429", "timeout", "ack_loss"])
def test_provider_failure_recovery(db, fixture, mode):
    now = [utc_now()]
    worker = OutboxWorker(db[0], provider=FakeProvider(db[0], mode), clock=lambda: now[0])
    money = reconcile(db[0])["counts"]
    for _ in range(3):
        assert worker.tick()
    assert reconcile(db[0])["counts"] == money
    now[0] += timedelta(seconds=10)
    healthy = OutboxWorker(db[0], clock=lambda: now[0])
    for _ in range(5):
        healthy.tick()
    assert count(db[0], "notification_effects") == 3
    assert reconcile(db[0])["status"] == "PASS"


def test_worker_crash_lease_expiry_dedupe(db, fixture):
    now = [utc_now()]

    def crash(point):
        if point == "AFTER_PROVIDER_DELIVERY_BEFORE_OUTBOX_ACK":
            raise RuntimeError("controlled worker crash")

    with pytest.raises(RuntimeError):
        OutboxWorker(db[0], clock=lambda: now[0], fault=crash).tick()
    assert count(db[0], "notification_effects") == 1
    now[0] += timedelta(seconds=31)
    worker = OutboxWorker(db[0], clock=lambda: now[0])
    while worker.tick():
        pass
    assert count(db[0], "notification_effects") == 3
    assert count(db[0], "inbox_receipts") == 3
    assert reconcile(db[0])["status"] == "PASS"


def test_bounded_dead_letter(db, fixture):
    now = [utc_now()]
    worker = OutboxWorker(
        db[0], provider=FakeProvider(db[0], "500"), clock=lambda: now[0], max_attempts=3
    )
    for _ in range(3):
        while worker.tick():
            pass
        now[0] += timedelta(seconds=10)
    with db[0].connect() as c:
        assert (
            c.execute(
                text("SELECT count(*) FROM outbox_events WHERE status='DEAD' AND attempt_count=3")
            ).scalar_one()
            == 3
        )
    report = reconcile(db[0])
    assert all(f["code"] == "OUTBOX_STUCK" for f in report["findings"])


def test_expired_lease_respects_retry_budget(db, fixture):
    now = [utc_now()]

    def crash(point):
        if point == "BEFORE_PROVIDER_DELIVERY":
            raise RuntimeError("crash before delivery")

    with pytest.raises(RuntimeError):
        OutboxWorker(db[0], clock=lambda: now[0], fault=crash, max_attempts=1).tick()
    now[0] += timedelta(seconds=31)
    worker = OutboxWorker(db[0], clock=lambda: now[0], max_attempts=1)
    while worker.tick():
        pass
    with db[0].connect() as c:
        assert (
            c.execute(
                text(
                    "SELECT count(*) FROM outbox_events WHERE status='DEAD' AND last_error_code='LEASE_RETRY_EXHAUSTED' AND attempt_count=1"
                )
            ).scalar_one()
            == 1
        )
