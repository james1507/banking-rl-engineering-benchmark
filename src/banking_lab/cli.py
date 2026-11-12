import argparse
import json
import os
import signal
import sys
from uuid import UUID

from banking_lab.application.reconciliation import reconcile
from banking_lab.application.seed import seed
from banking_lab.infrastructure.db import engine


def main() -> None:
    parser = argparse.ArgumentParser(description="Synthetic banking operations; no real money")
    parser.add_argument("command", choices=["seed", "reconcile", "worker", "submit"])
    parser.add_argument("--actor")
    parser.add_argument("--source")
    parser.add_argument("--destination")
    parser.add_argument("--amount", type=int, default=100)
    parser.add_argument("--key", default="cli-transfer-001")
    args = parser.parse_args()
    if args.command == "seed":
        print(json.dumps(seed(engine()), indent=2))
    elif args.command == "reconcile":
        report = reconcile(engine())
        print(json.dumps(report, indent=2))
        sys.exit(0 if report["status"] == "PASS" else 1)
    elif args.command == "submit":
        from banking_lab.application.transfers import TransferService, no_fault
        from banking_lab.domain.rules import TransferCommand

        point = os.environ.get("FAULT_POINT")

        def crash(here: str) -> None:
            if here == point:
                os._exit(86)

        result = TransferService(engine(), fault=crash if point else no_fault).create(
            UUID(args.actor),
            TransferCommand(UUID(args.source), UUID(args.destination), args.amount),
            args.key,
            "cli-submit",
        )
        print(
            json.dumps({"status": result.status, "body": result.body, "replayed": result.replayed})
        )
    else:
        from banking_lab.infrastructure.worker import OutboxWorker

        worker = OutboxWorker(engine())
        signal.signal(signal.SIGTERM, lambda *_: worker.stop())
        signal.signal(signal.SIGINT, lambda *_: worker.stop())
        worker.run()


if __name__ == "__main__":
    main()
