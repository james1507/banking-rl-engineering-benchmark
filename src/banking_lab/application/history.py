import base64
import hashlib
import hmac
import json
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Engine, text

from banking_lab.domain.rules import DomainError

TRANSFER_COLUMNS = "id,status,source_account_id,destination_account_id,amount_minor,currency,journal_group_id,created_at,completed_at,rejection_code,reference"


class HistoryService:
    def __init__(self, db: Engine, secret: str) -> None:
        self.db, self.secret = db, hashlib.sha256(("cursor:" + secret).encode()).digest()

    def accounts(self, actor: UUID, account: UUID | None = None) -> list[dict[str, Any]]:
        with self.db.connect() as c:
            rows = [
                dict(row)
                for row in c.execute(
                    text(
                        "SELECT id,account_type,currency,status,balance_minor,created_at FROM accounts WHERE owner_user_id=:actor AND (CAST(:id AS uuid) IS NULL OR id=CAST(:id AS uuid)) ORDER BY id"
                    ),
                    {"actor": actor, "id": str(account) if account else None},
                ).mappings()
            ]
        if account and not rows:
            raise DomainError("RESOURCE_NOT_FOUND", "Account unavailable.", 404)
        return rows

    def _encode(self, data: dict[str, Any]) -> str:
        raw = json.dumps(data, sort_keys=True, separators=(",", ":")).encode()
        signature = hmac.digest(self.secret, raw, "sha256")
        return base64.urlsafe_b64encode(signature + raw).decode().rstrip("=")

    def _decode(self, cursor: str, context: str) -> dict[str, Any]:
        try:
            if len(cursor) > 2048:
                raise ValueError
            data = base64.b64decode(
                cursor + "=" * (-len(cursor) % 4), altchars=b"-_", validate=True
            )
            signature, raw = data[:32], data[32:]
            if not hmac.compare_digest(signature, hmac.digest(self.secret, raw, "sha256")):
                raise ValueError
            obj = json.loads(raw)
            if obj["context"] != context:
                raise ValueError
            for name in ("last", "upper"):
                datetime.fromisoformat(obj[name][0])
                UUID(obj[name][1])
            return dict(obj)
        except (ValueError, KeyError, TypeError, IndexError) as exc:
            raise DomainError("VALIDATION_ERROR", "Invalid cursor or filter context.", 422) from exc

    def page(
        self,
        actor: UUID,
        *,
        account: UUID | None = None,
        limit: int = 20,
        cursor: str | None = None,
        status: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> dict[str, Any]:
        if not 1 <= limit <= 100 or status not in {None, "COMPLETED", "REJECTED"}:
            raise DomainError("VALIDATION_ERROR", "Invalid history filters.", 422)
        if account:
            self.accounts(actor, account)
        context = json.dumps([str(actor), str(account), status, str(since), str(until)])
        state = self._decode(cursor, context) if cursor else None
        if account:
            table, columns = (
                "ledger_postings",
                "id,journal_group_id,account_id,currency,signed_amount_minor,created_at,entry_sequence",
            )
            scope = "account_id=:account"
        else:
            table, columns = "transfers", TRANSFER_COLUMNS
            scope = "(actor_user_id=:actor OR source_account_id IN (SELECT id FROM accounts WHERE owner_user_id=:actor) OR destination_account_id IN (SELECT id FROM accounts WHERE owner_user_id=:actor))"
        params: dict[str, Any] = {"actor": actor, "account": account, "limit": limit + 1}
        clauses = [scope]
        if status and not account:
            clauses.append("status=:status")
            params["status"] = status
        for name, value, op in (("since", since, ">="), ("until", until, "<=")):
            if value:
                if value.tzinfo is None:
                    raise DomainError(
                        "VALIDATION_ERROR", "Filter timestamps require timezone.", 422
                    )
                clauses.append(f"created_at {op} :{name}")
                params[name] = value
        if state:
            for name, op in (("last", "<"), ("upper", "<=")):
                clauses.append(f"(created_at,id){op}(:{name}_at,CAST(:{name}_id AS uuid))")
                params[name + "_at"] = datetime.fromisoformat(state[name][0])
                params[name + "_id"] = state[name][1]
        with self.db.connect() as c:
            rows = [
                dict(row)
                for row in c.execute(
                    text(
                        f"SELECT {columns} FROM {table} WHERE {' AND '.join(clauses)} ORDER BY created_at DESC,id DESC LIMIT :limit"
                    ),
                    params,
                ).mappings()
            ]
        has_more, items = len(rows) > limit, rows[:limit]
        next_cursor = None
        if has_more:
            upper = (
                state["upper"]
                if state
                else [items[0]["created_at"].isoformat(), str(items[0]["id"])]
            )
            next_cursor = self._encode(
                {
                    "context": context,
                    "upper": upper,
                    "last": [items[-1]["created_at"].isoformat(), str(items[-1]["id"])],
                }
            )
        return {"items": items, "next_cursor": next_cursor, "has_more": has_more}

    def transfer(self, actor: UUID, transfer: UUID, *, admin: bool = False) -> dict[str, Any]:
        with self.db.connect() as c:
            row = (
                c.execute(
                    text(
                        f"SELECT {TRANSFER_COLUMNS} FROM transfers WHERE id=:id AND (:admin OR actor_user_id=:actor OR source_account_id IN (SELECT id FROM accounts WHERE owner_user_id=:actor) OR destination_account_id IN (SELECT id FROM accounts WHERE owner_user_id=:actor))"
                    ),
                    {"id": transfer, "actor": actor, "admin": admin},
                )
                .mappings()
                .one_or_none()
            )
        if row is None:
            raise DomainError("RESOURCE_NOT_FOUND", "Transfer unavailable.", 404)
        return dict(row)
