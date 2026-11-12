"""Public fault/scheduling adapter. Used only in disposable evaluation containers."""

import os
import socket
import threading
import time
from pathlib import Path

import psycopg

from banking_lab.api import routes
from banking_lab.application.transfers import TransferService
from banking_lab.main import app  # noqa: F401


def synchronize(request_id, point):
    folder = Path("/sync") / (request_id + "-" + point)
    folder.mkdir(exist_ok=True)
    (folder / (socket.gethostname() + "-" + str(threading.get_ident()))).touch()
    activity = None
    if point == "UNSAFE_ACCOUNT_READ":
        activity = psycopg.connect(
            os.environ["DATABASE_URL"].replace("postgresql+psycopg", "postgresql"),
            autocommit=True,
            connect_timeout=3,
            options="-c statement_timeout=1000",
        )
    try:
        deadline = time.monotonic() + 5
        while len(list(folder.iterdir())) < 2:
            # A correct locking solution may block its peer before this checkpoint.
            # Release that schedule without demanding removal of instrumentation.
            if (
                activity
                and activity.execute(
                    "SELECT EXISTS(SELECT 1 FROM pg_stat_activity WHERE usename=current_user AND pid<>pg_backend_pid() AND wait_event_type='Lock')"
                ).fetchone()[0]
            ):
                break
            if time.monotonic() > deadline:
                raise TimeoutError("Controlled schedule barrier timed out")
            time.sleep(0.005)
    finally:
        if activity:
            activity.close()


class InstrumentedService(TransferService):
    def create(self, actor, command, key, request_id, **kwargs):
        def hook(point):
            if request_id.startswith("race-") and point == "UNSAFE_ACCOUNT_READ":
                synchronize(request_id, point)
            if request_id.startswith("fault-" + point + "-"):
                os._exit(86)

        original = self.fault
        self.fault = hook
        try:
            # Synchronize before any candidate-owned transaction/lock, so alternative
            # correct serializable, actor-lock and optimistic designs remain valid.
            if request_id.startswith("race-"):
                synchronize(request_id, "REQUEST_START")
            return super().create(actor, command, key, request_id, **kwargs)
        finally:
            self.fault = original

    def __init__(self, db):
        super().__init__(db, fault=lambda point: None)


routes.TransferService = InstrumentedService
