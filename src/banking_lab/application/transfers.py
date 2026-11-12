import json
import random
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Connection, Engine, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.exc import TimeoutError as PoolTimeout

from banking_lab.domain.rules import (
    DomainError,
    TransferCommand,
    check_accounts,
    error_body,
    validate_key,
)
from banking_lab.infrastructure.repository import lock_accounts


@dataclass(frozen=True)
class Outcome:
    status: int
    body: dict[str, Any]
    replayed: bool = False


def no_fault(point: str) -> None:
    pass


def utc_now() -> datetime:
    return datetime.now(UTC)


def audit(
    c: Connection,
    actor: UUID | None,
    action: str,
    entity: UUID | None,
    outcome: str,
    request_id: str,
) -> None:
    c.execute(
        text(
            "INSERT INTO audit_events(id,actor_user_id,action,entity_id,outcome,request_id) VALUES(:id,:actor,:action,:entity,:outcome,:request_id)"
        ),
        {
            "id": uuid4(),
            "actor": actor,
            "action": action,
            "entity": entity,
            "outcome": outcome,
            "request_id": request_id,
        },
    )


class TransferService:
    def __init__(
        self,
        db: Engine,
        *,
        clock: Callable[[], datetime] = utc_now,
        ids: Callable[[], UUID] = uuid4,
        fault: Callable[[str], None] = no_fault,
    ) -> None:
        if fault is not no_fault:
            import os

            from banking_lab.infrastructure.db import require_local

            if os.environ.get("APP_ENV") != "test":
                raise ValueError("Fault injection requires APP_ENV=test")
            require_local(db.url.render_as_string(hide_password=False), disposable=True)
        self.db, self.clock, self.ids, self.fault = db, clock, ids, fault

    def create(
        self,
        actor: UUID,
        command: TransferCommand,
        key: str | None,
        request_id: str,
        *,
        funding: bool = False,
    ) -> Outcome:
        command.validate()
        safe_key = validate_key(key)
        for attempt in range(3):
            try:
                outcome = self._attempt(actor, command, safe_key, request_id, funding)
                self.fault("AFTER_SQL_COMMIT_BEFORE_HTTP_RESPONSE")
                return outcome
            except (DBAPIError, PoolTimeout) as exc:
                state = getattr(getattr(exc, "orig", None), "sqlstate", None)
                if state in {"40001", "40P01", "55P03"} and attempt < 2:
                    time.sleep(random.uniform(0.01, 0.03) * (2**attempt))
                    continue
                if state is None or state in {
                    "40001",
                    "40P01",
                    "55P03",
                    "57014",
                    "08006",
                    "08003",
                    "57P01",
                }:
                    raise DomainError(
                        "TRANSIENT_DATABASE_ERROR",
                        "Outcome uncertain; retry with the same key.",
                        503,
                    ) from exc
                raise
        raise AssertionError("unreachable")

    def _attempt(
        self, actor: UUID, command: TransferCommand, key: str, request_id: str, funding: bool
    ) -> Outcome:
        now, operation = self.clock(), "FUNDING" if funding else "TRANSFER"
        fingerprint = command.fingerprint(actor, operation)
        with self.db.begin() as c:
            active = c.execute(
                text("SELECT role FROM users WHERE id=:id AND status='ACTIVE' FOR SHARE"),
                {"id": actor},
            ).scalar_one_or_none()
            if active is None:
                raise DomainError("AUTH_INVALID", "Active user required.", 401)
            if funding and active != "ADMIN":
                raise DomainError("FORBIDDEN", "Funding requires admin seed control.", 403)
            c.execute(
                text("""INSERT INTO idempotency_records(id,actor_user_id,operation_type,key,request_hash,status,created_at,expires_at)
                VALUES(:id,:actor,:operation,:key,:hash,'IN_PROGRESS',:now,:expires)
                ON CONFLICT(actor_user_id,operation_type,key) DO NOTHING"""),
                {
                    "id": self.ids(),
                    "actor": actor,
                    "operation": operation,
                    "key": key,
                    "hash": fingerprint,
                    "now": now,
                    "expires": now + timedelta(days=1),
                },
            )
            record = (
                c.execute(
                    text(
                        "SELECT * FROM idempotency_records WHERE actor_user_id=:actor AND operation_type=:operation AND key=:key FOR UPDATE"
                    ),
                    {"actor": actor, "operation": operation, "key": key},
                )
                .mappings()
                .one()
            )
            if record["request_hash"] != fingerprint:
                raise DomainError("IDEMPOTENCY_KEY_REUSED", "Key belongs to a different request.")
            if record["status"] == "FINALIZED":
                audit(c, actor, "TRANSFER_REPLAY", record["transfer_id"], "REPLAYED", request_id)
                return Outcome(record["response_status"], record["response_body"], True)
            self.fault("BEFORE_ACCOUNT_LOCK")
            accounts = lock_accounts(
                c, command.source_account_id, command.destination_account_id, self.fault
            )
            source, destination = (
                accounts.get(command.source_account_id),
                accounts.get(command.destination_account_id),
            )
            if source is None or destination is None:
                raise DomainError("RESOURCE_NOT_FOUND", "Account unavailable.", 404)
            if (
                (
                    not funding
                    and (source["owner_user_id"] != actor or source["account_type"] != "CUSTOMER")
                )
                or (funding and source["account_type"] != "SYSTEM")
                or destination["account_type"] != "CUSTOMER"
            ):
                raise DomainError("RESOURCE_NOT_FOUND", "Account unavailable.", 404)
            transfer_id = self.ids()
            journal_id: UUID | None = None
            rejection: DomainError | None = None
            try:
                check_accounts(source, destination, command)
            except DomainError as exc:
                rejection = exc
            if rejection is None:
                journal_id = self.ids()
                self.fault("BEFORE_POSTING")
                c.execute(
                    text(
                        "INSERT INTO journal_groups(id,operation_type,business_reference_id,currency,posted_at) VALUES(:id,:op,:ref,:currency,:now)"
                    ),
                    {
                        "id": journal_id,
                        "op": operation,
                        "ref": transfer_id,
                        "currency": command.currency,
                        "now": now,
                    },
                )
                c.execute(
                    text(
                        "UPDATE accounts SET balance_minor=:balance,version=version+1,updated_at=:now WHERE id=:id"
                    ),
                    {
                        "balance": source["balance_minor"] - command.amount_minor,
                        "id": source["id"],
                        "now": now,
                    },
                )
                self.fault("AFTER_SOURCE_UPDATE")
                c.execute(
                    text(
                        "UPDATE accounts SET balance_minor=:balance,version=version+1,updated_at=:now WHERE id=:id"
                    ),
                    {
                        "balance": destination["balance_minor"] + command.amount_minor,
                        "id": destination["id"],
                        "now": now,
                    },
                )
                self.fault("BEFORE_LEDGER_INSERT")
                for sequence, account, amount in (
                    (1, source, -command.amount_minor),
                    (2, destination, command.amount_minor),
                ):
                    c.execute(
                        text(
                            "INSERT INTO ledger_postings(id,journal_group_id,account_id,currency,signed_amount_minor,created_at,entry_sequence) VALUES(:id,:group,:account,:currency,:amount,:now,:sequence)"
                        ),
                        {
                            "id": self.ids(),
                            "group": journal_id,
                            "account": account["id"],
                            "currency": command.currency,
                            "amount": amount,
                            "now": now,
                            "sequence": sequence,
                        },
                    )
            values = {
                "id": transfer_id,
                "actor": actor,
                "source": source["id"],
                "destination": destination["id"],
                "amount": command.amount_minor,
                "currency": command.currency,
                "status": "REJECTED" if rejection else "COMPLETED",
                "code": rejection.code if rejection else None,
                "group": journal_id,
                "idem": record["id"],
                "now": now,
                "completed": None if rejection else now,
                "request": request_id,
                "reference": command.reference,
            }
            c.execute(
                text("""INSERT INTO transfers(id,actor_user_id,source_account_id,destination_account_id,amount_minor,currency,status,rejection_code,journal_group_id,idempotency_record_id,created_at,completed_at,request_id,reference)
                VALUES(:id,:actor,:source,:destination,:amount,:currency,:status,:code,:group,:idem,:now,:completed,:request,:reference)"""),
                values,
            )
            if rejection:
                outcome = Outcome(
                    rejection.status, error_body(rejection.code, rejection.message, request_id)
                )
            else:
                c.execute(
                    text(
                        "INSERT INTO outbox_events(id,event_type,aggregate_id,payload_json,available_at,created_at) VALUES(:id,'TransferCompleted',:transfer,CAST(:payload AS jsonb),:now,:now)"
                    ),
                    {
                        "id": self.ids(),
                        "transfer": transfer_id,
                        "payload": json.dumps({"transfer_id": str(transfer_id)}),
                        "now": now,
                    },
                )
                outcome = Outcome(
                    201,
                    {
                        "id": str(transfer_id),
                        "status": "COMPLETED",
                        "source_account_id": str(source["id"]),
                        "destination_account_id": str(destination["id"]),
                        "amount_minor": command.amount_minor,
                        "currency": command.currency,
                        "journal_group_id": str(journal_id),
                        "created_at": now.isoformat().replace("+00:00", "Z"),
                        "completed_at": now.isoformat().replace("+00:00", "Z"),
                    },
                )
            c.execute(
                text(
                    "UPDATE idempotency_records SET status='FINALIZED',response_status=:status,response_body=CAST(:body AS jsonb),transfer_id=:transfer,finalized_at=:now WHERE id=:id"
                ),
                {
                    "status": outcome.status,
                    "body": json.dumps(outcome.body),
                    "transfer": transfer_id,
                    "now": now,
                    "id": record["id"],
                },
            )
            audit(c, actor, operation, transfer_id, values["status"], request_id)
            self.fault("BEFORE_SQL_COMMIT")
        return outcome
