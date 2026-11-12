from typing import Any
from uuid import UUID

from sqlalchemy import Engine, text

from banking_lab.application.transfers import audit
from banking_lab.domain.rules import DomainError


def get_reconciliation(db: Engine, run_id: UUID, actor: UUID) -> dict[str, Any]:
    with db.begin() as c:
        row = c.execute(
            text("SELECT report FROM reconciliation_runs WHERE id=:id"), {"id": run_id}
        ).scalar_one_or_none()
        audit(c, actor, "RECONCILIATION_READ", run_id, "FOUND" if row else "MISSING", "admin-read")
    if row is None:
        raise DomainError("RESOURCE_NOT_FOUND", "Run not found.", 404)
    return dict(row)
