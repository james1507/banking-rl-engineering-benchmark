import pytest
from sqlalchemy import create_engine

from banking_lab.application.reconciliation import reconcile
from banking_lab.application.transfers import TransferService
from banking_lab.domain.rules import DomainError, TransferCommand


def test_pool_exhaustion_is_bounded_and_recovers(db, fixture):
    limited = create_engine(
        db[0].url, pool_size=1, max_overflow=0, pool_timeout=0.1, hide_parameters=True
    )
    command = TransferCommand(fixture["alice_account"], fixture["bob_account"], 1)
    before = reconcile(db[0])["counts"]
    with limited.connect(), pytest.raises(DomainError) as caught:
        TransferService(limited).create(fixture["alice"], command, "pool-recovery-001", "pool")
    assert caught.value.status == 503
    assert reconcile(db[0])["counts"] == before
    assert (
        TransferService(limited)
        .create(fixture["alice"], command, "pool-recovery-001", "retry")
        .status
        == 201
    )
    assert reconcile(db[0])["status"] == "PASS"
    limited.dispose()
