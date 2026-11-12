"""Host-only, named incident rehearsals, each backed by disposable tests/evaluation."""

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS = {
    "INC-01": "tests/concurrency/test_concurrency.py::test_parallel_overspend_and_opposite",
    "INC-04": "tests/concurrency/test_concurrency.py::test_parallel_overspend_and_opposite",
    "INC-05": "tests/integration/test_money.py::test_database_guards_and_drift_detector",
    "INC-06": "tests/reliability/test_pool.py",
    "INC-07": "tests/reliability/test_worker.py::test_provider_failure_recovery",
    "INC-08": "tests/reliability/test_worker.py::test_worker_crash_lease_expiry_dedupe",
    "INC-10": "tests/integration/test_money.py::test_equal_timestamp_pages_and_tamper",
    "INC-11": "tests/security/test_api.py::test_bola_every_object",
    "INC-15": "tests/integration/test_limits.py",
}


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "INC-02"
    if name in {"INC-02", "INC-03"}:
        cmd = [
            sys.executable,
            "-m",
            "benchmark.cli",
            "run",
            "--task",
            "RL-02" if name == "INC-02" else "RL-03",
            "--mode",
            "golden",
        ]
    elif name in TESTS:
        cmd = [
            "docker",
            "compose",
            "run",
            "--rm",
            "-T",
            "tools",
            "scripts/run_tests.py",
            TESTS[name],
            "-q",
            "-s",
        ]
    else:
        raise SystemExit("Unknown/unimplemented scenario: " + name)
    target = ROOT / "artifacts/scenarios"
    target.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc).isoformat()
    with (target / (name + ".log")).open("w") as log:
        result = subprocess.run(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=600)
    report = {
        "scenario": name,
        "type": "simulated incident",
        "command": cmd,
        "started_at": started,
        "ended_at": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if result.returncode == 0 else "FAIL",
        "exit_code": result.returncode,
        "log": str((target / (name + ".log")).relative_to(ROOT)),
    }
    (target / (name + ".json")).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
