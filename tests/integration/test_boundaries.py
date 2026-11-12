from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import text

from banking_lab.application.reconciliation import reconcile
from banking_lab.application.transfers import TransferService
from banking_lab.domain.rules import MAX_MINOR, DomainError, TransferCommand


def test_smallest_exact_balance_and_missing(db, fixture):
    service = TransferService(db[0])
    cmd = TransferCommand(fixture["alice_account"], fixture["bob_account"], 100000)
    assert service.create(fixture["alice"], cmd, "exact-balance-001", "exact").status == 201
    rejected = service.create(
        fixture["alice"], replace(cmd, amount_minor=1), "one-over-0001", "one-over"
    )
    assert rejected.body["error"]["code"] == "INSUFFICIENT_FUNDS"
    missing = replace(cmd, source_account_id=uuid4())
    with pytest.raises(DomainError, match="RESOURCE_NOT_FOUND"):
        service.create(fixture["alice"], missing, "corrected-key-0001", "missing")
    assert (
        service.create(
            fixture["alice"],
            TransferCommand(fixture["alice_savings"], fixture["bob_account"], 1),
            "corrected-key-0001",
            "corrected",
        ).status
        == 201
    )
    assert reconcile(db[0])["status"] == "PASS"


def test_bigint_funding_overflow_is_safe(db, fixture):
    service = TransferService(db[0])
    # Total issued after this funding is MAX_MINOR+1, exactly abs(BIGINT_MIN).
    amount = MAX_MINOR + 1 - 300000
    funded = service.create(
        fixture["admin"],
        TransferCommand(fixture["treasury"], fixture["bob_account"], amount),
        "bigint-funding-001",
        "bigint",
        funding=True,
    )
    assert funded.status == 201
    # Move all but one cent from both Alice accounts into Bob: destination reaches MAX_MINOR.
    for index, source in enumerate((fixture["alice_account"], fixture["alice_savings"])):
        value = 100000 if index == 0 else 99999
        assert (
            service.create(
                fixture["alice"],
                TransferCommand(source, fixture["bob_account"], value),
                f"bigint-move-{index}",
                "bigint",
            ).status
            == 201
        )
    outcome = service.create(
        fixture["alice"],
        TransferCommand(fixture["alice_savings"], fixture["bob_account"], 1),
        "bigint-overflow-001",
        "overflow",
    )
    assert outcome.status == 422
    assert reconcile(db[0])["status"] == "PASS"


def test_currency_same_account_system_and_disabled(db, fixture):
    service = TransferService(db[0])
    account = uuid4()
    with db[1].begin() as c:
        c.execute(
            text(
                "INSERT INTO accounts(id,owner_user_id,account_type,currency) VALUES(:id,:owner,'CUSTOMER','EUR')"
            ),
            {"id": account, "owner": fixture["bob"]},
        )
    result = service.create(
        fixture["alice"],
        TransferCommand(fixture["alice_account"], account, 1),
        "currency-key-001",
        "currency",
    )
    assert result.body["error"]["code"] == "CURRENCY_MISMATCH"
    for cmd, code in (
        (
            TransferCommand(fixture["alice_account"], fixture["alice_account"], 1),
            "SAME_ACCOUNT_TRANSFER",
        ),
        (TransferCommand(fixture["treasury"], fixture["alice_account"], 1), "RESOURCE_NOT_FOUND"),
    ):
        with pytest.raises(DomainError, match=code):
            service.create(fixture["alice"], cmd, str(uuid4()), "invalid")
    with db[1].begin() as c:
        c.execute(text("UPDATE users SET status='DISABLED' WHERE id=:id"), {"id": fixture["alice"]})
    with pytest.raises(DomainError, match="AUTH_INVALID"):
        service.create(
            fixture["alice"],
            TransferCommand(fixture["alice_account"], fixture["bob_account"], 1),
            str(uuid4()),
            "disabled",
        )
