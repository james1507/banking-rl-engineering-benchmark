"""Copy actual sanitized local results; fail closed if a required verdict is absent."""

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
source = ROOT / "artifacts"
target = ROOT / "docs/evidence"
matrix = json.loads((source / "validation-matrix.json").read_text())
assert matrix["status"] == "PASS" and len(matrix["runs"]) == 56
for row in matrix["runs"]:
    assert row["status"] == row["expected"]
    report = source / "challenges" / f"{row['task']}-{row['mode']}-{row['seed']}.json"
    data = json.loads(report.read_text())
    assert data["status"] == row["expected"] and data["task_version"] == "1.0.2"
    assert data.get("tests", {}).get("skipped") == 0
    folder = target / "challenges"
    folder.mkdir(exist_ok=True)
    shutil.copy2(report, folder / report.name)
shutil.copy2(source / "validation-matrix.json", target / "validation-matrix.json")
for name in ("scenarios", "load"):
    folder = target / name
    folder.mkdir(exist_ok=True)
    for path in (source / name).glob("*"):
        if path.suffix == ".json" or (name == "scenarios" and path.suffix == ".log"):
            shutil.copy2(path, folder / path.name)
shutil.copy2(source / "backup/result.json", target / "backup-restore.json")
load = json.loads((source / "load/result.json").read_text())
assert load["status"] == "PASS" and load["invariants"]["invariant_violations"] == 0
rows = "\n".join(
    f"| {x['sample']} | {x['requests']} | {x['median_ms']:.2f} | {x['p95_ms']:.2f} |"
    for x in load["samples"]
)
(ROOT / "docs/performance.md").write_text(f"""# Measured local profile
Actual execution: {load["invariants"]["started_at"]}. Host Apple M2 Pro/16 GiB; Docker Desktop Linux aarch64, 10 CPUs exposed/8 GiB memory. M1 and remote amd64 were not executed.

3 samples, 50 unique successful HTTP transfers each, concurrency 10, 10 warmups. One-cent synthetic operations use real API/auth/PostgreSQL. Other local core/scenario containers may share CPU; no isolated production SLO claim.

| Sample | Requests | Median ms | p95 ms |
|---|---:|---:|---:|
{rows}

Generated 1,000 additional history transfers; final count {load["invariants"]["counts"]["transfers"]} transfers / {load["invariants"]["counts"]["ledger_postings"]} postings. Independent reconciliation found zero discrepancies. Actual EXPLAIN before/after native ANALYZE stored in evidence/load. Fresh fixture statistics can change plan selection; no universal latency/throughput improvement is asserted.

10k/100k datasets, contention scaling, p99 reliability and production availability remain unmeasured. Deferred projection guards recompute per-account sums; profile at larger volumes before optimization. No result was extrapolated into a production claim.
""")
(ROOT / "docs/evaluation-results.md").write_text("""# Actual task validation
Task version 1.0.2; pinned base commit in each metadata.json. See [complete matrix](evidence/validation-matrix.json) and [individual reports](evidence/challenges/).

| Task | Baseline five seeds | Golden five seeds | 8 negative controls | Alternative |
|---|---|---|---|---|
| RL-01 | FAIL × 5 expected | PASS × 5 | FAIL × 8 expected | optimistic CAS PASS; lock-only PASS |
| RL-02 | FAIL × 5 expected | PASS × 5 | FAIL × 8 expected | not required |
| RL-03 | FAIL × 5 expected | PASS × 5 | FAIL × 8 expected | not required |

56 actual evaluations matched expected verdicts; no skipped checks. Baseline candidate FAIL is expected data, never presented as a solved candidate. CLI rejects environment/timeouts/verifier errors as successful gates.

Seeds: 101, 202, 303, 404, 505. RL-01 golden has 20 synchronized overspend and 20 opposite-direction rounds per seed, plus unrelated-account liveness. RL-01/RL-02 have 100 same-key retry calls per run across two separate API processes. RL-03 checks actual process exit before posting, after source update, before commit and after commit/response loss. Independent SQL checks ledger/cache/status/idempotency/outbox; serial/authorization/strict validation regressions also tested.

Initial validation correctly remained FAIL when PID-namespaced partial RL-02 unexpectedly passed: both containers used PID 1. Initial failed matrix/log are preserved under evidence/initial-validation. Startup topology now uses direct and child-process launch, so PIDs differ; partial is rejected. Verifier and candidate image are frozen per run.

The successful historical 55-run version 1.0.1 matrix/log are preserved under evidence/pre-fairness-validation. Version 1.0.2 moves request synchronization before candidate transactions and releases the unsafe-read checkpoint when the peer is waiting on a PostgreSQL lock. This accepts correct implementations that retain the public callback or serialize the actor before account locking. The added lock-only solution changes only FOR UPDATE and keeps that callback. All 56 required evaluations were rerun against this final driver.

Reports include actual measured duration, dependency/image/environment digests, failure codes and SQL findings. Public source/solutions are transparent portfolio artifacts, not a secret internet benchmark. Runtime grading does not mount them into candidate containers.
""")
(target / "README.md").write_text("""# Evidence index
Actual local runs, 12 November 2026. Hardware: Apple M2 Pro/16 GiB; Docker Desktop Linux aarch64, 10 CPUs exposed, 8 GiB allocated. No actual M1, remote amd64, GitHub Actions run, production deployment or external review claim.

| Evidence | What executed |
|---|---|
| [final-core.log](final-core.log) | make ci: Ruff/format, strict mypy, application tests and reconciliation |
| [readme-tests.xml](readme-tests.xml), [readme-verification.log](readme-verification.log) | Fresh README verification: all 62 pytest cases; complete IDs in [catalogue](../test-catalogue.md) |
| [reviewer reports](reviewer/), [screenshots and provenance](../assets/screenshots/README.md) | Seven static reports derived from recorded evidence; actual browser captures, plus live Swagger |
| [readme-static.log](readme-static.log), [readme-assets-check.log](readme-assets-check.log) | Documentation helper lint/format/type checks; local links, eight embedded images and provenance hashes verified |
| [validation-matrix.json](validation-matrix.json), [reports](challenges/) | 56 expected candidate verdicts, task version 1.0.2: 3 tasks, 5 seeds, 8 negative controls, optimistic and lock-only alternatives |
| [initial-validation](initial-validation/) | Preserved failed first matrix exposing PID-local partial control weakness |
| [pre-fairness-validation](pre-fairness-validation/) | Preserved successful 55-run version 1.0.1 matrix before scheduler fairness fix |
| [scenario-validation.log](scenario-validation.log), [scenario reports/logs](scenarios/) | INC-01–08, INC-10/11/15, each isolated |
| [backup-restore.json](backup-restore.json), [log](backup-restore.log) | New-DB logical restore, equal counts/ledger/replay digests, clean reconciliation |
| [load result](load/result.json), [query plan](load/history-explain.json) | 3 × 50 real HTTP transfers, concurrency 10, 10 warmups, 1k extra history transfers |
| [dependency-audit.log](dependency-audit.log) | Locked runtime dependency audit, no known vulnerabilities at actual run |
| [sandbox-self-check.log](sandbox-self-check.log) | Golden fidelity and actual no-reference/no-verifier/no-socket/read-only sandbox checks |
| [demo-flow.log](demo-flow.log), [running-services.log](running-services.log) | Real live transfer/replay, health, service status |

Earlier sanitized failed logs document issues discovered, not final failures concealed as passes. Final checkpoint is authoritative. Optional collector/Prometheus/Grafana configs were not executed; 10k/100k load, advanced tasks, operator UI, HA/PITR and full release qualification remain open.
""")
print(
    "Published actual matrix/reports, 11 scenarios, restore and measured profile; no synthetic PASS rows."
)
