import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

from prometheus_client import Counter, Histogram

REQUESTS = Counter("http_requests_total", "HTTP requests", ["route", "method", "status_class"])
LATENCY = Histogram("http_request_duration_seconds", "HTTP latency", ["route"])


class JSONLog(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        data: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "severity": record.levelname,
            "service": "banking-lab",
            "operation": record.getMessage(),
        }
        data.update(getattr(record, "safe_fields", {}))
        return json.dumps(data, default=str)


logger = logging.getLogger("banking_lab")
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JSONLog())
logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False
