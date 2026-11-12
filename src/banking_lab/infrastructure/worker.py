import threading
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Engine, text

from banking_lab.application.transfers import no_fault, utc_now
from banking_lab.observability.telemetry import logger


class ProviderError(Exception):
    pass


class FakeProvider:
    """Local, transactional receiver. No external email/SMS integration."""

    def __init__(self, db: Engine, mode: str = "healthy") -> None:
        if mode not in {"healthy", "500", "429", "timeout", "ack_loss"}:
            raise ValueError("Unknown fake-provider mode")
        self.db, self.mode = db, mode

    def deliver(self, event_id: UUID, now: datetime) -> None:
        if self.mode in {"500", "429", "timeout"}:
            raise ProviderError("PROVIDER_" + self.mode.upper())
        with self.db.begin() as c:
            inserted = c.execute(
                text(
                    "INSERT INTO inbox_receipts(event_id,consumer_name,processed_at) VALUES(:id,'fake-notification',:now) ON CONFLICT DO NOTHING RETURNING event_id"
                ),
                {"id": event_id, "now": now},
            ).scalar_one_or_none()
            if inserted:
                c.execute(
                    text("INSERT INTO notification_effects(event_id,created_at) VALUES(:id,:now)"),
                    {"id": event_id, "now": now},
                )
        if self.mode == "ack_loss":
            raise ProviderError("PROVIDER_ACK_LOST")


class OutboxWorker:
    def __init__(
        self,
        db: Engine,
        *,
        provider: FakeProvider | None = None,
        clock: Callable[[], datetime] = utc_now,
        fault: Callable[[str], None] = no_fault,
        max_attempts: int = 5,
    ) -> None:
        self.db, self.provider, self.clock = db, provider or FakeProvider(db), clock
        self.fault, self.max_attempts = fault, max_attempts
        self.stopped = threading.Event()

    def stop(self) -> None:
        self.stopped.set()

    def claim(self) -> dict[str, Any] | None:
        now, token = self.clock(), uuid4()
        with self.db.begin() as c:
            row = (
                c.execute(
                    text(
                        "SELECT * FROM outbox_events WHERE (status='PENDING' AND available_at<=:now) OR (status='LEASED' AND leased_until<=:now) ORDER BY created_at,id LIMIT 1 FOR UPDATE SKIP LOCKED"
                    ),
                    {"now": now},
                )
                .mappings()
                .one_or_none()
            )
            if row is None:
                return None
            event = dict(row)
            c.execute(
                text(
                    "UPDATE outbox_events SET status='LEASED',lease_token=:token,leased_until=:until,attempt_count=attempt_count+1 WHERE id=:id"
                ),
                {"id": event["id"], "token": token, "until": now + timedelta(seconds=30)},
            )
            event.update(lease_token=token, attempt_count=event["attempt_count"] + 1)
            return event

    def tick(self) -> bool:
        event = self.claim()
        if event is None:
            return False
        now = self.clock()
        self.fault("BEFORE_PROVIDER_DELIVERY")
        try:
            self.provider.deliver(event["id"], now)
        except ProviderError as exc:
            with self.db.begin() as c:
                c.execute(
                    text(
                        "UPDATE outbox_events SET status=:status,available_at=:due,leased_until=NULL,lease_token=NULL,last_error_code=:code WHERE id=:id AND lease_token=:token"
                    ),
                    {
                        "id": event["id"],
                        "token": event["lease_token"],
                        "status": "DEAD"
                        if event["attempt_count"] >= self.max_attempts
                        else "PENDING",
                        "due": now + timedelta(seconds=min(60, 2 ** event["attempt_count"])),
                        "code": str(exc),
                    },
                )
            logger.warning(
                "outbox.retry",
                extra={
                    "safe_fields": {
                        "event_id": str(event["id"]),
                        "error_code": str(exc),
                        "retry_count": event["attempt_count"],
                    }
                },
            )
            return True
        self.fault("AFTER_PROVIDER_DELIVERY_BEFORE_OUTBOX_ACK")
        with self.db.begin() as c:
            c.execute(
                text(
                    "UPDATE outbox_events SET status='PUBLISHED',published_at=:now,leased_until=NULL,lease_token=NULL,last_error_code=NULL WHERE id=:id AND lease_token=:token"
                ),
                {"id": event["id"], "token": event["lease_token"], "now": now},
            )
        logger.info(
            "outbox.published",
            extra={
                "safe_fields": {"event_id": str(event["id"]), "retry_count": event["attempt_count"]}
            },
        )
        return True

    def run(self) -> None:
        while not self.stopped.is_set():
            try:
                if not self.tick():
                    self.stopped.wait(1)
            except Exception as exc:
                logger.error(
                    "outbox.failure", extra={"safe_fields": {"exception_type": type(exc).__name__}}
                )
                self.stopped.wait(1)
