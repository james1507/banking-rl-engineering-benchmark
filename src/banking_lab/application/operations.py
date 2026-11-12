from typing import Any
from uuid import UUID

from sqlalchemy import Connection, Engine, text

from banking_lab.application.transfers import audit
from banking_lab.domain.rules import DomainError


def require_admin(c: Connection, actor: UUID) -> None:
    role = c.execute(
        text("SELECT role FROM users WHERE id=:id AND status='ACTIVE'"), {"id": actor}
    ).scalar_one_or_none()
    if role != "ADMIN":
        raise DomainError("FORBIDDEN", "Admin role required.", 403)


def get_reconciliation(db: Engine, run_id: UUID, actor: UUID) -> dict[str, Any]:
    with db.begin() as c:
        require_admin(c, actor)
        row = c.execute(
            text("SELECT report FROM reconciliation_runs WHERE id=:id"), {"id": run_id}
        ).scalar_one_or_none()
        audit(c, actor, "RECONCILIATION_READ", run_id, "FOUND" if row else "MISSING", "admin-read")
    if row is None:
        raise DomainError("RESOURCE_NOT_FOUND", "Run not found.", 404)
    return dict(row)


def configure_limit(
    db: Engine, actor: UUID, kind: str, subject: UUID, amount: int, request_id: str
) -> dict[str, Any]:
    from banking_lab.domain.rules import MAX_MINOR

    if kind not in {"ACCOUNT", "USER"} or type(amount) is not int or not 1 <= amount <= MAX_MINOR:
        raise DomainError("VALIDATION_ERROR", "Invalid transfer limit.", 422)
    with db.begin() as c:
        role = c.execute(
            text("SELECT role FROM users WHERE id=:id AND status='ACTIVE'"), {"id": actor}
        ).scalar_one_or_none()
        if role != "ADMIN":
            raise DomainError("FORBIDDEN", "Admin role required.", 403)
        table = "accounts" if kind == "ACCOUNT" else "users"
        target = c.execute(
            text(f"SELECT id FROM {table} WHERE id=:id FOR NO KEY UPDATE"), {"id": subject}
        ).scalar_one_or_none()
        if target is None:
            raise DomainError("RESOURCE_NOT_FOUND", "Limit subject unavailable.", 404)
        c.execute(
            text(
                "INSERT INTO transfer_limits(subject_type,subject_id,daily_minor) VALUES(:kind,:id,:amount) ON CONFLICT(subject_type,subject_id) DO UPDATE SET daily_minor=:amount,updated_at=now()"
            ),
            {"kind": kind, "id": subject, "amount": amount},
        )
        audit(c, actor, "TRANSFER_LIMIT_SET", subject, "SUCCESS", request_id)
    return {"subject_type": kind, "subject_id": str(subject), "daily_minor": amount}


def list_outbox(db: Engine, actor: UUID, limit: int) -> list[dict[str, Any]]:
    with db.begin() as c:
        require_admin(c, actor)
        rows = [
            dict(row)
            for row in c.execute(
                text(
                    "SELECT id,event_type,aggregate_id,status,attempt_count,available_at,created_at,published_at,last_error_code FROM outbox_events ORDER BY created_at DESC,id DESC LIMIT :limit"
                ),
                {"limit": limit},
            ).mappings()
        ]
        audit(c, actor, "OUTBOX_READ", None, "SUCCESS", "admin-read")
        return rows


def retry_outbox(db: Engine, actor: UUID, event: UUID, request_id: str) -> None:
    with db.begin() as c:
        require_admin(c, actor)
        updated = c.execute(
            text(
                "UPDATE outbox_events SET status='PENDING',available_at=now(),lease_token=NULL,leased_until=NULL,last_error_code=NULL WHERE id=:id AND status='DEAD' RETURNING id"
            ),
            {"id": event},
        ).scalar_one_or_none()
        if updated is None:
            raise DomainError("RESOURCE_NOT_FOUND", "Dead-letter event unavailable.", 404)
        audit(c, actor, "OUTBOX_RETRY", event, "SUCCESS", request_id)
