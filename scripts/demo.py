"""Synthetic one-cent transfer and exact replay using stdlib HTTP client; never prints tokens."""

import json
import urllib.request
from pathlib import Path
from uuid import NAMESPACE_URL, uuid4, uuid5

values = dict(
    line.split("=", 1)
    for line in Path(".env").read_text().splitlines()
    if "=" in line and not line.startswith("#")
)
base = "http://127.0.0.1:" + values.get("API_PORT", "8010") + "/api/v1"


def post(path, body, headers=None):
    request = urllib.request.Request(
        base + path,
        json.dumps(body).encode(),
        {"Content-Type": "application/json", **(headers or {})},
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        return response.status, json.load(response)


_, login = post("/auth/login", {"email": "alice@example.test", "password": values["DEMO_PASSWORD"]})
headers = {"Authorization": "Bearer " + login["access_token"], "Idempotency-Key": str(uuid4())}
body = {
    "source_account_id": str(uuid5(NAMESPACE_URL, "synthetic-banking-lab/demo/alice_account")),
    "destination_account_id": str(uuid5(NAMESPACE_URL, "synthetic-banking-lab/demo/bob_account")),
    "amount_minor": 1,
    "currency": "USD",
    "reference": "synthetic-demo",
}
first = post("/transfers", body, headers)
second = post("/transfers", body, headers)
assert first == second and first[0] == 201
print(json.dumps({"transfer": first[1], "exact_replay": first == second}, indent=2))
