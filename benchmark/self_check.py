"""Runnable host checks for packaging boundary and golden patch fidelity."""

import json
import subprocess
import tempfile
from pathlib import Path

from benchmark.cli import IMAGE, ROOT, materialize, metadata


def main():
    for task in ("RL-01", "RL-02", "RL-03"):
        folder, meta = metadata(task)
        assert 0 < meta["time_limit_seconds"] <= 900
        assert 0 < meta["cpu_limit"] <= 2 and 0 < meta["memory_limit_mb"] <= 2048
        assert json.loads((folder / "metadata.json").read_text()) == meta
        with tempfile.TemporaryDirectory() as temporary:
            candidate = Path(temporary).resolve() / "candidate"
            materialize(task, "golden", candidate)
            assert not (candidate / "benchmark").exists()
            assert not (candidate / "challenges").exists()
            assert not list(candidate.rglob("golden.patch"))
            assert not list(candidate.rglob("test_behavior.py"))
            code = "import os; from pathlib import Path; assert os.geteuid()!=0; assert not any(Path(p).exists() for p in ['/app/src','/app/benchmark','/app/challenges','/verifier','/var/run/docker.sock']); caught=False\ntry: Path('/candidate/instruction.md').write_text('tamper')\nexcept OSError: caught=True\nassert caught"
            subprocess.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "--network",
                    "none",
                    "--read-only",
                    "--cap-drop",
                    "ALL",
                    "--security-opt",
                    "no-new-privileges",
                    "-v",
                    str(candidate) + ":/candidate:ro",
                    IMAGE,
                    "python",
                    "-c",
                    code,
                ],
                check=True,
            )
            for name in (
                "src/banking_lab/infrastructure/repository.py",
                "src/banking_lab/application/transfers.py",
                "alembic/versions/0001_core.sql",
            ):
                expected = subprocess.check_output(
                    ["git", "show", meta["base_revision"] + ":" + name], cwd=ROOT
                )
                assert (candidate / name).read_bytes() == expected, task + " golden drift: " + name
    print(
        "3 task metadata/package/golden fidelity checks passed; no verifier/solution in candidate."
    )


if __name__ == "__main__":
    main()
