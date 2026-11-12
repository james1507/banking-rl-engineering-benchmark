# RL-03: Atomic Posting and Crash Recovery
Killing a process during posting can leave a debit without its matching journal/credit. Some database safety guards were weakened during a recent optimization.

Fix the real service across process boundaries while preserving `/api/v1` contracts.
All amounts are integer USD minor units. Only source owners can debit. A completed transfer has two opposite postings and matching balances. Identical actor/operation/key/body must replay original status/body; conflicting payload must return 409. Terminal insufficient-funds outcomes must replay. Crash before commit leaves no state; crash after commit must be safely recoverable.

Allowed: src/, Alembic migrations, public tests. Preserve APIs and immutable history. Do not disable transfers, alter verifier, hard-code identities/amounts, rely on process-only locks, or remove ledger evidence. Test scheduling/fault adapter is public infrastructure, not part of your fix.

Public check: `pytest tests/unit`. Inspect schema and service and add focused checks. Evaluator runs separate processes, randomized deterministic fixtures, DB invariant queries, bounded deadlines and adjacent healthy/security behavior. CPU 2, RAM 1024 MB, evaluation deadline 300 seconds; no internet, host mounts or Docker socket. Source starts from pinned base d1cee249883627d9bca4371aa547d6c16d7c3303 with isolated defect patch.

Submit by running `python3 -m benchmark.cli run --task RL-03 --mode candidate --candidate /absolute/path/to/workspace` from trusted repository host. Never mount verifier/reference files into solving workspace.
