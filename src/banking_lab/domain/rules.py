import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any
from uuid import UUID

MAX_MINOR = 2**63 - 1
MIN_MINOR = -(2**63)


class DomainError(Exception):
    def __init__(self, code: str, message: str, status: int = 409) -> None:
        self.code, self.message, self.status = code, message, status
        super().__init__(code)


def error_body(code: str, message: str, request_id: str) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "request_id": request_id, "details": {}}}


@dataclass(frozen=True)
class TransferCommand:
    source_account_id: UUID
    destination_account_id: UUID
    amount_minor: int
    currency: str = "USD"
    reference: str | None = None

    def validate(self) -> None:
        if type(self.amount_minor) is not int or not 1 <= self.amount_minor <= MAX_MINOR:
            raise DomainError("VALIDATION_ERROR", "Amount must be a positive BIGINT integer.", 422)
        if self.currency != "USD":
            raise DomainError("VALIDATION_ERROR", "Only USD is supported.", 422)
        if self.source_account_id == self.destination_account_id:
            raise DomainError("SAME_ACCOUNT_TRANSFER", "Source and destination must differ.", 422)
        if self.reference is not None and (
            not isinstance(self.reference, str) or len(self.reference) > 140
        ):
            raise DomainError("VALIDATION_ERROR", "Reference exceeds 140 characters.", 422)

    def fingerprint(self, actor: UUID, operation: str) -> str:
        payload = {**asdict(self), "actor": actor, "operation": operation}
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
        ).hexdigest()


def validate_key(key: str | None) -> str:
    if key is None:
        raise DomainError("IDEMPOTENCY_KEY_REQUIRED", "Idempotency-Key is required.", 422)
    if not 8 <= len(key) <= 128 or not all(33 <= ord(c) <= 126 for c in key):
        raise DomainError(
            "VALIDATION_ERROR", "Key must contain 8–128 visible ASCII characters.", 422
        )
    return key


def check_accounts(
    source: dict[str, Any], destination: dict[str, Any], command: TransferCommand
) -> None:
    for account in (source, destination):
        if account["status"] != "ACTIVE":
            code = "ACCOUNT_FROZEN" if account["status"] == "FROZEN" else "ACCOUNT_CLOSED"
            raise DomainError(code, "Account is not eligible for transfers.")
        if account["currency"] != command.currency:
            raise DomainError("CURRENCY_MISMATCH", "Account currencies must match.")
    if source["account_type"] == "CUSTOMER" and source["balance_minor"] < command.amount_minor:
        raise DomainError(
            "INSUFFICIENT_FUNDS", "The available balance is not sufficient for this transfer."
        )
    if (
        destination["balance_minor"] > MAX_MINOR - command.amount_minor
        or source["balance_minor"] < MIN_MINOR + command.amount_minor
    ):
        raise DomainError("VALIDATION_ERROR", "Balance would exceed BIGINT bounds.", 422)
