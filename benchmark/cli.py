"""Host-only trusted orchestrator. Candidate code is never imported/executed on host."""

import argparse
import hashlib
import io
import json
import secrets
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
IMAGE = "banking-rl-sandbox:local"
PG_IMAGE = (
    "postgres:16-alpine@sha256:aa6cb33cf4c19c765cefcf48d96176258800870a9a1e930ad126200f9d825139"
)
MODES = [
    "baseline",
    "golden",
    "noop",
    "partial",
    "hardcoded",
    "canned",
    "disabled",
    "suppress",
    "delete-evidence",
    "unit-only",
    "alternative",
    "lock-only",
    "candidate",
]


def command(args, *, check=True, timeout=90, data=None):
    result = subprocess.run(args, cwd=ROOT, input=data, capture_output=True, timeout=timeout)
    if check and result.returncode:
        # Never echo command/env because they can contain disposable credentials.
        raise RuntimeError(
            "Tool failed: " + str(args[0]) + "; " + result.stderr.decode(errors="replace")[-1500:]
        )
    return result


def metadata(task):
    matches = []
    for path in (ROOT / "challenges").glob("*/metadata.json"):
        obj = json.loads(path.read_text())
        if obj.get("id") == task:
            matches.append((path.parent, obj))
    if len(matches) != 1:
        raise ValueError("Unknown or duplicate task ID: " + task)
    path, obj = matches[0]
    required = {
        "id": str,
        "title": str,
        "base_revision": str,
        "task_version": str,
        "time_limit_seconds": int,
        "memory_limit_mb": int,
        "cpu_limit": int,
    }
    if any(not isinstance(obj.get(k), v) for k, v in required.items()):
        raise ValueError("Invalid task metadata schema")
    if len(obj["base_revision"]) != 40 or obj["memory_limit_mb"] > 2048 or obj["cpu_limit"] > 2:
        raise ValueError("Unsafe task resources/base revision")
    return path, obj


def patch(workspace, path):
    command(["git", "apply", "--unsafe-paths", "--directory", str(workspace), str(path)])


def materialize(task, mode, output, candidate=None):
    folder, meta = metadata(task)
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    archive = command(
        [
            "git",
            "archive",
            meta["base_revision"],
            "src",
            "alembic",
            "alembic.ini",
            "pyproject.toml",
            "uv.lock",
            "tests/unit",
        ]
    ).stdout
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        for entry in tar.getmembers():
            if (
                entry.issym()
                or entry.islnk()
                or Path(entry.name).is_absolute()
                or ".." in Path(entry.name).parts
            ):
                raise ValueError("Unsafe source archive")
        tar.extractall(output)
    patch(output, folder / "environment/bug.patch")
    if mode == "golden":
        patch(output, folder / "solution/golden.patch")
    elif mode in {"alternative", "lock-only"}:
        patch(output, folder / ("solution/" + mode + ".patch"))
    elif mode in {
        "partial",
        "hardcoded",
        "canned",
        "disabled",
        "suppress",
        "delete-evidence",
        "unit-only",
    }:
        mutation = folder / "controls" / (mode + ".patch")
        if mutation.stat().st_size:
            patch(output, mutation)
    elif mode == "candidate":
        if not candidate:
            raise ValueError("--candidate path required")
        for name in ("src", "alembic"):
            source = Path(candidate).resolve() / name
            if not source.is_dir() or any(p.is_symlink() for p in source.rglob("*")):
                raise ValueError("Candidate must have source/migrations without symlinks")
            shutil.rmtree(output / name)
            shutil.copytree(source, output / name)
    shutil.copy2(ROOT / "benchmark/public_driver.py", output / "public_driver.py")
    shutil.copy2(folder / "instruction.md", output / "instruction.md")
    return meta


def ensure_image():
    # Fast cached rebuild ensures stripped image tracks actual dependency image.
    command(["docker", "build", "-f", "infra/sandbox.Dockerfile", "-t", IMAGE, "."], timeout=180)


def evaluate(task, mode, seed=101, candidate=None):
    folder, meta = metadata(task)
    started = time.monotonic()
    run_id = "lab-eval-" + uuid4().hex[:12]
    net = run_id + "-net"
    volume = run_id + "-sync"
    pg = run_id + "-db"
    candidates = [run_id + "-a", run_id + "-b"]
    report = {
        "task_id": task,
        "candidate": mode,
        "task_version": meta["task_version"],
        "seed": seed,
        "base_revision": meta["base_revision"],
        "artifacts": [],
    }
    root = Path(tempfile.mkdtemp(prefix="banking-eval-")).resolve()
    try:
        image_id = (
            command(["docker", "image", "inspect", IMAGE, "--format", "{{.Id}}"])
            .stdout.decode()
            .strip()
        )
        materialize(task, mode, root / "candidate", candidate)
        verifier_file = root / "verifier.py"
        shutil.copy2(ROOT / "benchmark/verifier.py", verifier_file)
        command(["docker", "network", "create", "--internal", net])
        command(["docker", "volume", "create", volume])
        command(
            [
                "docker",
                "run",
                "--rm",
                "--network",
                "none",
                "--user",
                "0",
                "-v",
                volume + ":/sync",
                image_id,
                "chmod",
                "777",
                "/sync",
            ]
        )
        owner_password = secrets.token_hex(24)
        app_password = secrets.token_hex(24)
        secret = secrets.token_hex(32)
        dbname = "lab_eval_" + uuid4().hex[:12]
        command(
            [
                "docker",
                "run",
                "-d",
                "--name",
                pg,
                "--network",
                net,
                "--network-alias",
                "db",
                "--memory",
                "512m",
                "--cpus",
                "1",
                "-e",
                "POSTGRES_USER=lab_owner",
                "-e",
                "POSTGRES_PASSWORD=" + owner_password,
                "-e",
                "POSTGRES_DB=" + dbname,
                PG_IMAGE,
            ]
        )
        for _ in range(100):
            ready = command(
                [
                    "docker",
                    "exec",
                    pg,
                    "pg_isready",
                    "-h",
                    "127.0.0.1",
                    "-U",
                    "lab_owner",
                    "-d",
                    dbname,
                ],
                check=False,
            )
            if ready.returncode == 0:
                break
            time.sleep(0.1)
        else:
            raise RuntimeError("Disposable PostgreSQL failed startup")
        command(
            [
                "docker",
                "exec",
                "-i",
                pg,
                "psql",
                "-U",
                "lab_owner",
                "-d",
                dbname,
                "-v",
                "ON_ERROR_STOP=1",
            ],
            data=(
                "CREATE ROLE lab_app LOGIN PASSWORD '"
                + app_password
                + "'; REVOKE CREATE ON SCHEMA public FROM PUBLIC; GRANT USAGE ON SCHEMA public TO lab_app;"
            ).encode(),
        )
        owner_url = f"postgresql+psycopg://lab_owner:{owner_password}@db:5432/{dbname}"
        app_url = f"postgresql+psycopg://lab_app:{app_password}@db:5432/{dbname}"
        mount = str(root / "candidate") + ":/candidate:ro"
        common = [
            "--network",
            net,
            "--read-only",
            "--tmpfs",
            "/tmp:rw,nosuid,size=128m",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--pids-limit",
            "128",
            "--memory",
            str(meta["memory_limit_mb"]) + "m",
            "--cpus",
            str(meta["cpu_limit"]),
        ]
        command(
            [
                "docker",
                "run",
                "--rm",
                "--name",
                run_id + "-migration",
                *common,
                "-v",
                mount,
                "-e",
                "DATABASE_URL=" + owner_url,
                "-e",
                "PYTHONDONTWRITEBYTECODE=1",
                image_id,
                "alembic",
                "-c",
                "/candidate/alembic.ini",
                "upgrade",
                "head",
            ]
        )
        for index, name in enumerate(candidates):
            command(
                [
                    "docker",
                    "run",
                    "-d",
                    "--name",
                    name,
                    "--restart",
                    "on-failure:10",
                    *common,
                    "--network-alias",
                    "candidate-" + ("a" if index == 0 else "b"),
                    "-v",
                    mount,
                    "-v",
                    volume + ":/sync",
                    "-e",
                    "DATABASE_URL=" + app_url,
                    "-e",
                    "JWT_SECRET=" + secret,
                    "-e",
                    "APP_ENV=test",
                    "-e",
                    "PYTHONDONTWRITEBYTECODE=1",
                    image_id,
                    *(
                        [
                            "uvicorn",
                            "public_driver:app",
                            "--host",
                            "0.0.0.0",
                            "--port",
                            "8000",
                            "--no-access-log",
                        ]
                        if index == 0
                        else [
                            "sh",
                            "-c",
                            "uvicorn public_driver:app --host 0.0.0.0 --port 8000 --no-access-log; exit $?",
                        ]
                    ),
                ]
            )
        verifier = command(
            [
                "docker",
                "run",
                "--rm",
                "--name",
                run_id + "-verifier",
                *common,
                "-v",
                str(verifier_file) + ":/verifier/verifier.py:ro",
                "-e",
                "PYTHONPATH=",
                "-e",
                "TASK_ID=" + task,
                "-e",
                "RUN_SEED=" + str(seed),
                "-e",
                "JWT_SECRET=" + secret,
                "-e",
                "VERIFIER_DATABASE_URL=" + owner_url.replace("postgresql+psycopg", "postgresql"),
                image_id,
                "python",
                "/verifier/verifier.py",
            ],
            timeout=meta["time_limit_seconds"],
        )
        lines = verifier.stdout.decode().splitlines()
        results = [
            json.loads(line[len("RESULT_JSON:") :])
            for line in lines
            if line.startswith("RESULT_JSON:")
        ]
        if len(results) != 1:
            raise RuntimeError("Missing or ambiguous verifier report")
        result = results[0]
        if result.get("status") not in {"PASS", "FAIL", "VERIFIER_ERROR"}:
            raise RuntimeError("Invalid verifier status")
        report.update(result)
        report["verifier_digest"] = (
            "sha256:" + hashlib.sha256(verifier_file.read_bytes()).hexdigest()
        )
        manifest = hashlib.sha256()
        for file in sorted((root / "candidate").rglob("*")):
            if file.is_file():
                manifest.update(str(file.relative_to(root / "candidate")).encode())
                manifest.update(file.read_bytes())
        report["candidate_artifact_digest"] = "sha256:" + manifest.hexdigest()
        report["environment_digest"] = (
            "sha256:"
            + hashlib.sha256(
                (
                    image_id
                    + PG_IMAGE
                    + hashlib.sha256((ROOT / "uv.lock").read_bytes()).hexdigest()
                ).encode()
            ).hexdigest()
        )
        report["dependency_lock_digest"] = (
            "sha256:" + hashlib.sha256((ROOT / "uv.lock").read_bytes()).hexdigest()
        )
        report["candidate_image_id"] = image_id
        report["postgres_image"] = PG_IMAGE
    except subprocess.TimeoutExpired:
        report.update(status="TIMEOUT", failure_codes=["EXECUTION_TIMEOUT"])
    except Exception as exc:
        report.update(
            status="ENVIRONMENT_ERROR", failure_codes=[type(exc).__name__], message=str(exc)[:1500]
        )
    finally:
        report["wall_duration_ms"] = round((time.monotonic() - started) * 1000)
        report["executed_at"] = datetime.now(timezone.utc).isoformat()
        for name in candidates + [pg, run_id + "-verifier", run_id + "-migration"]:
            command(["docker", "rm", "-f", name], check=False)
        command(["docker", "volume", "rm", volume], check=False)
        command(["docker", "network", "rm", net], check=False)
        shutil.rmtree(root)
    artifacts = ROOT / "artifacts/challenges"
    artifacts.mkdir(parents=True, exist_ok=True)
    path = artifacts / f"{task}-{mode}-{seed}.json"
    report["artifacts"] = [str(path.relative_to(ROOT))]
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            {
                "task": task,
                "candidate": mode,
                "seed": seed,
                "status": report["status"],
                "tests": report.get("tests"),
                "report": str(path.relative_to(ROOT)),
            }
        ),
        flush=True,
    )
    return report


def validate(tasks, seeds):
    matrix = []
    for task in tasks:
        for seed in seeds:
            for mode in ("baseline", "golden"):
                report = evaluate(task, mode, seed)
                matrix.append(
                    {
                        "task": task,
                        "mode": mode,
                        "seed": seed,
                        "status": report["status"],
                        "expected": "FAIL" if mode == "baseline" else "PASS",
                    }
                )
        for mode in (
            "noop",
            "partial",
            "hardcoded",
            "canned",
            "disabled",
            "suppress",
            "delete-evidence",
            "unit-only",
        ):
            report = evaluate(task, mode, seeds[0])
            matrix.append(
                {
                    "task": task,
                    "mode": mode,
                    "seed": seeds[0],
                    "status": report["status"],
                    "expected": "FAIL",
                }
            )
        if task == "RL-01":
            report = evaluate(task, "lock-only", seeds[0])
            matrix.append(
                {
                    "task": task,
                    "mode": "lock-only",
                    "seed": seeds[0],
                    "status": report["status"],
                    "expected": "PASS",
                }
            )
            report = evaluate(task, "alternative", seeds[0])
            matrix.append(
                {
                    "task": task,
                    "mode": "alternative",
                    "seed": seeds[0],
                    "status": report["status"],
                    "expected": "PASS",
                }
            )
    ok = all(row["status"] == row["expected"] for row in matrix)
    path = ROOT / "artifacts/validation-matrix.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(
        json.dumps({"status": "PASS" if ok else "FAIL", "runs": matrix}, indent=2) + "\n"
    )
    print("Task validation: " + ("PASS" if ok else "FAIL"), flush=True)
    return ok


def main():
    def terminate(signum, frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, terminate)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["run", "validate", "materialize"])
    parser.add_argument("--task", choices=["RL-01", "RL-02", "RL-03"])
    parser.add_argument("--mode", choices=MODES, default="golden")
    parser.add_argument("--seed", type=int, default=101)
    parser.add_argument("--seeds", default="101,202,303,404,505")
    parser.add_argument("--output")
    parser.add_argument("--candidate")
    args = parser.parse_args()
    if args.action == "materialize":
        if not args.task or not args.output:
            parser.error("--task and --output required")
        materialize(args.task, "baseline", args.output)
        print("Public defective workspace: " + args.output)
        return
    ensure_image()
    if args.action == "validate":
        ok = validate(
            [args.task] if args.task else ["RL-01", "RL-02", "RL-03"],
            [int(s) for s in args.seeds.split(",")],
        )
        sys.exit(0 if ok else 1)
    if not args.task:
        parser.error("--task required")
    report = evaluate(args.task, args.mode, args.seed, args.candidate)
    expected = (
        "FAIL"
        if args.mode
        in {
            "baseline",
            "noop",
            "partial",
            "hardcoded",
            "canned",
            "disabled",
            "suppress",
            "delete-evidence",
            "unit-only",
        }
        else "PASS"
    )
    sys.exit(
        0
        if report["status"] == expected
        else (2 if report["status"] not in {"PASS", "FAIL"} else 1)
    )


if __name__ == "__main__":
    main()
