from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest
from sqlalchemy import text

from banking_lab.config import settings


def payload(f):
    return {
        "source_account_id": str(f["alice_account"]),
        "destination_account_id": str(f["bob_account"]),
        "amount_minor": 12500,
        "currency": "USD",
    }


def test_api_contract(client, fixture, alice_headers):
    assert client.get("/health/live").status_code == 200
    assert client.get("/health/ready").status_code == 200
    assert client.get("/api/v1/accounts").status_code == 401
    assert len(client.get("/api/v1/accounts", headers=alice_headers).json()) == 2
    headers = {**alice_headers, "Idempotency-Key": "api-key-0001", "X-Request-ID": "contract-0001"}
    first = client.post("/api/v1/transfers", headers=headers, json=payload(fixture))
    assert first.status_code == 201, first.text
    assert first.headers["x-request-id"] == "contract-0001"
    second = client.post("/api/v1/transfers", headers=headers, json=payload(fixture))
    assert first.json() == second.json() and second.headers["idempotent-replayed"] == "true"
    assert (
        client.get("/api/v1/transfers/" + first.json()["id"], headers=alice_headers).status_code
        == 200
    )
    assert client.get(
        "/api/v1/accounts/" + str(fixture["alice_account"]) + "/statement", headers=alice_headers
    ).json()["items"]
    assert (
        client.post("/api/v1/transfers", headers=alice_headers, json=payload(fixture)).json()[
            "error"
        ]["code"]
        == "IDEMPOTENCY_KEY_REQUIRED"
    )


def test_bola_every_object(client, fixture, alice_headers):
    foreign = str(fixture["bob_account"])
    for path in ("/api/v1/accounts/" + foreign, "/api/v1/accounts/" + foreign + "/statement"):
        response = client.get(path, headers=alice_headers)
        assert response.status_code == 404 and "balance_minor" not in response.text
    for path in (
        "/api/v1/transfers/" + str(uuid4()),
        "/api/v1/admin/reconciliation-runs/" + str(uuid4()),
    ):
        assert client.get(path, headers=alice_headers).status_code in {403, 404}
    p = payload(fixture)
    p["source_account_id"] = foreign
    p["destination_account_id"] = str(fixture["alice_account"])
    assert (
        client.post(
            "/api/v1/transfers",
            headers={**alice_headers, "Idempotency-Key": "bola-key-0001"},
            json=p,
        ).status_code
        == 404
    )
    assert (
        client.post("/api/v1/admin/reconciliation-runs", headers=alice_headers).status_code == 403
    )


def test_refresh_reuse_and_logout(client, fixture):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "ALICE@example.test", "password": "test-password-strong"},
    ).json()
    first = {"refresh_token": login["refresh_token"]}
    rotated = client.post("/api/v1/auth/refresh", json=first)
    assert rotated.status_code == 200
    assert client.post("/api/v1/auth/refresh", json=first).status_code == 401
    assert (
        client.post(
            "/api/v1/auth/refresh", json={"refresh_token": rotated.json()["refresh_token"]}
        ).status_code
        == 401
    )
    fresh = client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.test", "password": "test-password-strong"},
    ).json()
    body = {"refresh_token": fresh["refresh_token"]}
    assert client.post("/api/v1/auth/logout", json=body).status_code == 204
    assert client.post("/api/v1/auth/logout", json=body).status_code == 204
    assert client.post("/api/v1/auth/refresh", json=body).status_code == 401


@pytest.mark.parametrize(
    "field,value",
    [
        ("amount_minor", True),
        ("amount_minor", 1.0),
        ("amount_minor", "1e3"),
        ("amount_minor", 2**63),
        ("status", "COMPLETED"),
        ("currency", "VND"),
    ],
)
def test_dto_mass_assignment(client, fixture, alice_headers, field, value):
    p = payload(fixture)
    p[field] = value
    assert (
        client.post(
            "/api/v1/transfers",
            headers={**alice_headers, "Idempotency-Key": "bad-input-0001"},
            json=p,
        ).status_code
        == 422
    )


def test_json_policy_request_size(client, fixture, alice_headers):
    headers = {
        **alice_headers,
        "Content-Type": "application/json",
        "Idempotency-Key": "json-policy-0001",
    }
    assert (
        client.post(
            "/api/v1/transfers", headers=headers, content='{"amount_minor":1,"amount_minor":2}'
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/transfers", headers=headers, content="[" + " " * 65536 + "]"
        ).status_code
        == 413
    )
    assert client.get("/nonexistent").json()["error"]["code"] == "RESOURCE_NOT_FOUND"


@pytest.mark.parametrize("change", ["expired", "issuer", "audience", "signature", "none"])
def test_jwt_validation(client, fixture, change):
    config = settings()
    now = datetime.now(UTC)
    p = {
        "sub": str(fixture["alice"]),
        "iss": config.jwt_issuer,
        "aud": config.jwt_audience,
        "iat": now,
        "exp": now + timedelta(minutes=1),
        "jti": str(uuid4()),
    }
    if change == "expired":
        p["exp"] = now - timedelta(seconds=1)
    if change == "issuer":
        p["iss"] = "wrong"
    if change == "audience":
        p["aud"] = "wrong"
    token = jwt.encode(
        p,
        "wrong-secret-long-enough-123456789"
        if change == "signature"
        else ("" if change == "none" else config.jwt_secret),
        algorithm="none" if change == "none" else "HS256",
    )
    assert client.get("/api/v1/me", headers={"Authorization": "Bearer " + token}).status_code == 401


def test_disabled_user_and_rate_limit(client, fixture, alice_headers, db):
    with db[1].begin() as c:
        c.execute(text("UPDATE users SET status='DISABLED' WHERE id=:id"), {"id": fixture["alice"]})
    assert client.get("/api/v1/me", headers=alice_headers).status_code == 401
    for _ in range(10):
        client.post(
            "/api/v1/auth/login", json={"email": "missing@example.test", "password": "bad-password"}
        )
    assert (
        client.post(
            "/api/v1/auth/login", json={"email": "missing@example.test", "password": "bad-password"}
        ).status_code
        == 429
    )
