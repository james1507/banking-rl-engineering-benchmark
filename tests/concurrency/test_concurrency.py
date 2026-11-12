from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from sqlalchemy import text

from banking_lab.application.reconciliation import reconcile
from banking_lab.application.transfers import TransferService
from banking_lab.domain.rules import TransferCommand


def test_100_same_key(db, fixture):
    command = TransferCommand(fixture["alice_account"], fixture["bob_account"], 100)

    def call(_):
        return TransferService(db[0]).create(
            fixture["alice"], command, "hundred-key-0001", "parallel"
        )

    with ThreadPoolExecutor(max_workers=16) as pool:
        results = list(pool.map(call, range(100)))
    assert len({r.body["id"] for r in results}) == 1
    assert all(r.status == 201 for r in results)
    assert sum(not r.replayed for r in results) == 1
    assert reconcile(db[0])["status"] == "PASS"


def test_parallel_overspend_and_opposite(db, fixture):
    barrier = Barrier(2)

    def fault(point):
        if point == "BEFORE_ACTOR_LOCK":
            barrier.wait(timeout=5)

    def debit(n):
        return TransferService(db[0], fault=fault).create(
            fixture["alice"],
            TransferCommand(fixture["alice_account"], fixture["bob_account"], 70000),
            f"overspend-key-{n}",
            "concurrent",
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(debit, range(2)))
    assert sorted(r.status for r in results) == [201, 409]
    for n in range(20):
        barrier = Barrier(2)

        def opposite(reverse, n=n):
            actor, source, dest = (
                (fixture["bob"], fixture["bob_account"], fixture["alice_account"])
                if reverse
                else (fixture["alice"], fixture["alice_account"], fixture["bob_account"])
            )
            return TransferService(db[0], fault=fault).create(
                actor, TransferCommand(source, dest, 1), f"opposite-{n}-{reverse}", "opposite"
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(opposite, [False, True]))
        assert all(r.status == 201 for r in results)
    assert reconcile(db[0])["status"] == "PASS"
    with db[0].connect() as c:
        assert (
            c.execute(
                text("SELECT min(balance_minor) FROM accounts WHERE account_type='CUSTOMER'")
            ).scalar_one()
            >= 0
        )
