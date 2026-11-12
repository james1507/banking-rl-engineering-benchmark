import ast
from pathlib import Path
from uuid import uuid4

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from banking_lab.api.dto import Transfer
from banking_lab.domain.rules import MAX_MINOR, DomainError, TransferCommand, validate_key
from banking_lab.infrastructure.db import require_local


@pytest.mark.parametrize("amount", [True, False, 1.0, "1", 0, -1, 2**63, None])
def test_strict_amount(amount):
    with pytest.raises(ValidationError):
        Transfer(source_account_id=uuid4(), destination_account_id=uuid4(), amount_minor=amount)


@given(st.integers(min_value=1, max_value=MAX_MINOR))
def test_minor_unit_roundtrip(amount):
    command = TransferCommand(uuid4(), uuid4(), amount)
    command.validate()
    assert command.amount_minor == amount


def test_fingerprint_scope_and_key():
    a, b, actor = uuid4(), uuid4(), uuid4()
    x = TransferCommand(a, b, 10)
    assert x.fingerprint(actor, "TRANSFER") == x.fingerprint(actor, "TRANSFER")
    assert x.fingerprint(actor, "TRANSFER") != x.fingerprint(uuid4(), "TRANSFER")
    assert x.fingerprint(actor, "TRANSFER") != TransferCommand(a, b, 11).fingerprint(
        actor, "TRANSFER"
    )
    for value in (None, "short", "x" * 129, "bad key 000"):
        with pytest.raises(DomainError):
            validate_key(value)


def test_database_guard():
    for url in ("postgresql://prod.example/banking", "postgresql://localhost/banking_lab"):
        with pytest.raises(ValueError):
            require_local(url, disposable=True)
    require_local("postgresql://db/lab_test_123", disposable=True)


def test_domain_dependency_direction():
    for path in Path("src/banking_lab/domain").glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.ImportFrom):
                assert not any(
                    value in (node.module or "")
                    for value in ("fastapi", "sqlalchemy", "infrastructure", "application", "api.")
                )
