"""Independent aggregate SQL. Never imports posting code or repairs financial state."""

import json
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Engine, text

from banking_lab.application.transfers import utc_now

CHECKS = {
    "BALANCE_DRIFT": """SELECT a.id FROM accounts a LEFT JOIN ledger_postings p ON p.account_id=a.id GROUP BY a.id HAVING a.balance_minor<>coalesce(sum(p.signed_amount_minor),0)""",
    "INVALID_JOURNAL": """SELECT g.id FROM journal_groups g LEFT JOIN ledger_postings p ON p.journal_group_id=g.id LEFT JOIN accounts a ON a.id=p.account_id GROUP BY g.id HAVING count(p.id)<>2 OR coalesce(sum(p.signed_amount_minor),0)<>0 OR count(*) FILTER(WHERE p.currency<>g.currency OR p.currency<>a.currency)>0""",
    "INVALID_TRANSFER": """SELECT t.id FROM transfers t WHERE (t.status='COMPLETED' AND (SELECT count(*) FROM ledger_postings p JOIN journal_groups g ON g.id=p.journal_group_id WHERE g.id=t.journal_group_id AND g.business_reference_id=t.id AND p.currency=t.currency AND ((p.account_id=t.source_account_id AND p.signed_amount_minor=-t.amount_minor) OR (p.account_id=t.destination_account_id AND p.signed_amount_minor=t.amount_minor)))<>2) OR (t.status='REJECTED' AND t.journal_group_id IS NOT NULL) OR t.status='PENDING'""",
    "INVALID_IDEMPOTENCY": """SELECT i.id FROM idempotency_records i LEFT JOIN transfers t ON t.id=i.transfer_id WHERE i.status<>'FINALIZED' OR t.id IS NULL OR t.idempotency_record_id<>i.id OR (t.status='COMPLETED' AND (i.response_status<>201 OR i.response_body->>'id'<>t.id::text OR i.response_body->>'status'<>'COMPLETED')) OR (t.status='REJECTED' AND i.response_body->'error'->>'code' IS DISTINCT FROM t.rejection_code)""",
    "MISSING_EVENT": """SELECT t.id FROM transfers t LEFT JOIN outbox_events o ON o.aggregate_id=t.id WHERE (t.status='COMPLETED' AND o.id IS NULL) OR (t.status<>'COMPLETED' AND o.id IS NOT NULL)""",
    "ORPHAN_JOURNAL": """SELECT g.id FROM journal_groups g LEFT JOIN transfers t ON t.journal_group_id=g.id WHERE t.id IS NULL""",
    "NEGATIVE_CUSTOMER": "SELECT id FROM accounts WHERE account_type='CUSTOMER' AND balance_minor<0",
    "OUTBOX_STUCK": "SELECT id FROM outbox_events WHERE status='DEAD' OR (status<>'PUBLISHED' AND created_at<:checked_at-interval '10 minutes')",
    "INVALID_NOTIFICATION": "SELECT e.event_id AS id FROM notification_effects e LEFT JOIN inbox_receipts i ON i.event_id=e.event_id WHERE i.event_id IS NULL",
}


def reconcile(
    db: Engine,
    *,
    persist: bool = False,
    actor: UUID | None = None,
    request_id: str = "reconcile",
    checked_at: datetime | None = None,
) -> dict[str, Any]:
    started = utc_now()
    with db.connect().execution_options(isolation_level="REPEATABLE READ") as c, c.begin():
        c.execute(text("SET TRANSACTION READ ONLY"))
        findings = [
            {"code": code, "severity": "HIGH", "entity_id": str(row[0])}
            for code, query in CHECKS.items()
            for row in c.execute(text(query), {"checked_at": checked_at or started})
        ]
        counts = {
            name: c.execute(text(f"SELECT count(*) FROM {name}")).scalar_one()
            for name in (
                "accounts",
                "transfers",
                "journal_groups",
                "ledger_postings",
                "idempotency_records",
                "outbox_events",
            )
        }
        revision = c.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    report = {
        "id": str(uuid4()),
        "started_at": started.isoformat(),
        "ended_at": utc_now().isoformat(),
        "schema_revision": revision,
        "checked_through": (checked_at or started).isoformat(),
        "status": "FAIL" if findings else "PASS",
        "counts": counts,
        "findings": findings,
        "invariant_violations": len(findings),
    }
    if persist:
        from banking_lab.application.transfers import audit

        with db.begin() as c:
            c.execute(
                text(
                    "INSERT INTO reconciliation_runs(id,started_at,ended_at,status,report) VALUES(:id,:start,:end,:status,CAST(:report AS jsonb))"
                ),
                {
                    "id": UUID(report["id"]),
                    "start": started,
                    "end": utc_now(),
                    "status": report["status"],
                    "report": json.dumps(report),
                },
            )
            audit(c, actor, "RECONCILE", UUID(report["id"]), report["status"], request_id)
    return report
