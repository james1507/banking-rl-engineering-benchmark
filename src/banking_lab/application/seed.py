import os
from uuid import NAMESPACE_URL, UUID, uuid5

from argon2 import PasswordHasher
from sqlalchemy import Engine, text

from banking_lab.application.transfers import TransferService
from banking_lab.domain.rules import TransferCommand
from banking_lab.infrastructure.db import require_local


def fixture_id(name: str) -> UUID:
    return uuid5(NAMESPACE_URL, "synthetic-banking-lab/" + name)


def seed(
    db: Engine, password: str | None = None, *, prefix: str = "demo", balance: int = 100_000
) -> dict[str, str]:
    require_local(db.url.render_as_string(hide_password=False))
    secret = password or os.environ.get("DEMO_PASSWORD", "")
    if len(secret) < 12:
        raise ValueError("Set DEMO_PASSWORD with at least 12 characters; no default password")
    ids = {
        name: fixture_id(prefix + "/" + name)
        for name in (
            "alice",
            "bob",
            "admin",
            "alice_account",
            "alice_savings",
            "bob_account",
            "treasury",
        )
    }
    password_hash = PasswordHasher().hash(secret)
    with db.begin() as c:
        for name in ("alice", "bob", "admin"):
            c.execute(
                text(
                    "INSERT INTO users(id,email,password_hash,role) VALUES(:id,:email,:hash,:role) ON CONFLICT DO NOTHING"
                ),
                {
                    "id": ids[name],
                    "email": name + "@example.test"
                    if prefix == "demo"
                    else name + "+" + prefix + "@example.test",
                    "hash": password_hash,
                    "role": "ADMIN" if name == "admin" else "USER",
                },
            )
        for name, owner in (
            ("alice_account", "alice"),
            ("alice_savings", "alice"),
            ("bob_account", "bob"),
            ("treasury", None),
        ):
            c.execute(
                text(
                    "INSERT INTO accounts(id,owner_user_id,account_type,currency) VALUES(:id,:owner,:kind,'USD') ON CONFLICT DO NOTHING"
                ),
                {
                    "id": ids[name],
                    "owner": ids[owner] if owner else None,
                    "kind": "CUSTOMER" if owner else "SYSTEM",
                },
            )
    for name in ("alice_account", "alice_savings", "bob_account"):
        TransferService(db).create(
            ids["admin"],
            TransferCommand(ids["treasury"], ids[name], balance),
            "seed-funding-" + name,
            "seed-" + prefix,
            funding=True,
        )
    return {name: str(value) for name, value in ids.items()}
