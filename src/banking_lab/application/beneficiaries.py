from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Engine, text

from banking_lab.application.transfers import audit
from banking_lab.domain.rules import DomainError


# ponytail: local list caps at 100; add signed keyset paging for larger address books.
def beneficiaries(db: Engine, actor: UUID) -> list[dict[str, Any]]:
    with db.connect() as c:
        return [
            dict(row)
            for row in c.execute(
                text(
                    "SELECT id,target_account_id,alias,status,created_at FROM beneficiaries WHERE owner_user_id=:actor ORDER BY created_at DESC,id DESC LIMIT 100"
                ),
                {"actor": actor},
            ).mappings()
        ]


def create_beneficiary(
    db: Engine, actor: UUID, target: UUID, alias: str, request_id: str
) -> dict[str, Any]:
    with db.begin() as c:
        eligible = c.execute(
            text(
                "SELECT id FROM accounts WHERE id=:target AND account_type='CUSTOMER' AND status='ACTIVE'"
            ),
            {"target": target},
        ).scalar_one_or_none()
        if eligible is None:
            raise DomainError("RESOURCE_NOT_FOUND", "Target unavailable.", 404)
        row = (
            c.execute(
                text(
                    "INSERT INTO beneficiaries(id,owner_user_id,target_account_id,alias) VALUES(:id,:actor,:target,:alias) ON CONFLICT(owner_user_id,target_account_id) DO NOTHING RETURNING id,target_account_id,alias,status,created_at"
                ),
                {"id": uuid4(), "actor": actor, "target": target, "alias": alias},
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise DomainError("BENEFICIARY_EXISTS", "Beneficiary already exists.")
        audit(c, actor, "BENEFICIARY_CREATE", row["id"], "SUCCESS", request_id)
        return dict(row)


def update_beneficiary(
    db: Engine, actor: UUID, beneficiary: UUID, alias: str, status: str, request_id: str
) -> dict[str, Any]:
    with db.begin() as c:
        row = (
            c.execute(
                text(
                    "UPDATE beneficiaries SET alias=:alias,status=:status WHERE id=:id AND owner_user_id=:actor RETURNING id,target_account_id,alias,status,created_at"
                ),
                {"id": beneficiary, "actor": actor, "alias": alias, "status": status},
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise DomainError("RESOURCE_NOT_FOUND", "Beneficiary unavailable.", 404)
        audit(c, actor, "BENEFICIARY_UPDATE", beneficiary, "SUCCESS", request_id)
        return dict(row)
