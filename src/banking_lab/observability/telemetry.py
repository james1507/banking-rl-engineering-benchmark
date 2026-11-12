import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

from opentelemetry import trace
from prometheus_client import Counter, Histogram

REQUESTS = Counter("http_requests_total", "HTTP requests", ["route", "method", "status_class"])
LATENCY = Histogram("http_request_duration_seconds", "HTTP latency", ["route"])


TRANSFER_ATTEMPTS = Counter("transfer_attempts_total", "Transfer attempts", ["outcome"])
REPLAYS = Counter("idempotency_replays_total", "Durable response replays")
CONFLICTS = Counter("idempotency_key_conflicts_total", "Key fingerprint conflicts")
DB_RETRIES = Counter("transfer_retries_total", "Whole-transaction retries", ["reason"])
POSTING_DURATION = Histogram("transfer_posting_duration_seconds", "Posting/replay duration")


class JSONLog(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        data: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "severity": record.levelname,
            "service": "banking-lab",
            "operation": record.getMessage(),
            "event": record.getMessage(),
        }
        span = trace.get_current_span().get_span_context()
        if span.is_valid:
            data.update(
                trace_id=format(span.trace_id, "032x"), span_id=format(span.span_id, "016x")
            )
        data.update(getattr(record, "safe_fields", {}))
        return json.dumps(data, default=str)


logger = logging.getLogger("banking_lab")
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JSONLog())
logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False
