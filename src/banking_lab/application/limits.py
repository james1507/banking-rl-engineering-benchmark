from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import Connection, text

from banking_lab.domain.rules import DomainError


def enforce_limits(c: Connection, actor: UUID, source: UUID, amount: int, now: datetime) -> None:
    start = now.astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    for kind, subject, column in (
        ("USER", actor, "actor_user_id"),
        ("ACCOUNT", source, "source_account_id"),
    ):
        limit = c.execute(
            text(
                "SELECT daily_minor FROM transfer_limits WHERE subject_type=:kind AND subject_id=:id FOR SHARE"
            ),
            {"kind": kind, "id": subject},
        ).scalar_one_or_none()
        if limit is None:
            continue
        total = c.execute(
            text(
                f"SELECT coalesce(sum(amount_minor),0) FROM transfers WHERE {column}=:id AND status='COMPLETED' AND created_at>=:start AND created_at<:end"
            ),
            {"id": subject, "start": start, "end": start + timedelta(days=1)},
        ).scalar_one()
        if total + amount > limit:
            raise DomainError("TRANSFER_LIMIT_EXCEEDED", "Daily UTC outgoing limit exceeded.")
