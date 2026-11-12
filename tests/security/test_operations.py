from sqlalchemy import text


def test_beneficiary_owner_and_admin_boundaries(client, fixture, alice_headers, db):
    created = client.post(
        "/api/v1/beneficiaries",
        headers=alice_headers,
        json={"target_account_id": str(fixture["bob_account"]), "alias": "Synthetic Bob"},
    )
    assert created.status_code == 201
    bid = created.json()["id"]
    bob = client.post(
        "/api/v1/auth/login", json={"email": "bob@example.test", "password": "test-password-strong"}
    ).json()
    headers = {"Authorization": "Bearer " + bob["access_token"]}
    assert (
        client.patch(
            "/api/v1/beneficiaries/" + bid,
            headers=headers,
            json={"alias": "other", "status": "DISABLED"},
        ).status_code
        == 404
    )
    assert client.get("/api/v1/beneficiaries", headers=headers).json() == []
    assert (
        client.patch(
            "/api/v1/beneficiaries/" + bid,
            headers=alice_headers,
            json={"alias": "Renamed", "status": "DISABLED"},
        ).status_code
        == 200
    )
    assert client.get("/api/v1/admin/outbox-events", headers=alice_headers).status_code == 403
    assert (
        client.put(
            "/api/v1/admin/transfer-limits",
            headers=alice_headers,
            json={"subject_type": "USER", "subject_id": str(fixture["alice"]), "daily_minor": 100},
        ).status_code
        == 403
    )
    admin = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.test", "password": "test-password-strong"},
    ).json()
    admin_headers = {"Authorization": "Bearer " + admin["access_token"]}
    assert (
        client.put(
            "/api/v1/admin/transfer-limits",
            headers=admin_headers,
            json={"subject_type": "USER", "subject_id": str(fixture["alice"]), "daily_minor": 100},
        ).status_code
        == 200
    )
    events = client.get("/api/v1/admin/outbox-events", headers=admin_headers)
    assert events.status_code == 200 and "payload_json" not in events.text
    report = client.post("/api/v1/admin/reconciliation-runs", headers=admin_headers)
    assert report.status_code == 201 and report.json()["status"] == "PASS"
    run_id = report.json()["id"]
    assert (
        client.get("/api/v1/admin/reconciliation-runs/" + run_id, headers=admin_headers).status_code
        == 200
    )
    assert (
        client.get("/api/v1/admin/reconciliation-runs/" + run_id, headers=alice_headers).status_code
        == 403
    )
    with db[1].begin() as c:
        c.execute(
            text("UPDATE outbox_events SET status='DEAD' WHERE id=:id"),
            {"id": events.json()[0]["id"]},
        )
    assert (
        client.post(
            "/api/v1/admin/outbox-events/" + events.json()[0]["id"] + "/retry",
            headers=admin_headers,
        ).status_code
        == 200
    )
