import os
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from banking_lab.application.seed import seed
from banking_lab.infrastructure.db import engine, require_local


@pytest.fixture
def db():
    url = os.environ.get("TEST_OWNER_URL")
    if not url:
        pytest.fail("Use make test; TEST_OWNER_URL must name disposable DB")
    require_local(url, disposable=True)
    owner = create_engine(url)
    with owner.begin() as c:
        c.execute(
            text(
                "TRUNCATE users,accounts,journal_groups,idempotency_records,transfers,ledger_postings,outbox_events,audit_events,refresh_sessions,login_buckets,inbox_receipts,notification_effects,reconciliation_runs,beneficiaries CASCADE"
            )
        )
    yield engine(), owner
    owner.dispose()


@pytest.fixture
def fixture(db):
    return {key: UUID(value) for key, value in seed(db[0], "test-password-strong").items()}


@pytest.fixture
def client(db):
    from banking_lab.main import app

    with TestClient(app) as client:
        yield client


@pytest.fixture
def alice_headers(client, fixture):
    result = client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.test", "password": "test-password-strong"},
    )
    assert result.status_code == 200, result.text
    return {"Authorization": "Bearer " + result.json()["access_token"]}
