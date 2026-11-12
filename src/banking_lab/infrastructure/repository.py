from collections.abc import Callable
from typing import Any
from uuid import UUID

from sqlalchemy import Connection, text


def lock_accounts(
    c: Connection, source: UUID, destination: UUID, fault: Callable[[str], None]
) -> dict[UUID, dict[str, Any]]:
    rows = c.execute(
        text("SELECT * FROM accounts WHERE id IN (:source,:destination) ORDER BY id FOR UPDATE"),
        {"source": source, "destination": destination},
    ).mappings()
    return {row["id"]: dict(row) for row in rows}
