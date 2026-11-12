# Executed application test catalogue

Source: [JUnit](evidence/readme-tests.xml), [make ci log](evidence/readme-verification.log). Executed 2026-11-12T03:23:57.428155+00:00; 62 passed, zero failures/errors/skips. Parameterized entries count separately. Hypothesis examples are not counted as separate test cases.


## Money, concurrency & crash recovery

| Executed test case | Source | Time (s) | Result |
|---|---|---:|---|
| `test_100_same_key` | [tests/concurrency/test_concurrency.py](../tests/concurrency/test_concurrency.py) | 0.296 | PASS |
| `test_parallel_overspend_and_opposite` | [tests/concurrency/test_concurrency.py](../tests/concurrency/test_concurrency.py) | 0.330 | PASS |
| `test_smallest_exact_balance_and_missing` | [tests/integration/test_boundaries.py](../tests/integration/test_boundaries.py) | 0.138 | PASS |
| `test_bigint_funding_overflow_is_safe` | [tests/integration/test_boundaries.py](../tests/integration/test_boundaries.py) | 0.130 | PASS |
| `test_currency_same_account_system_and_disabled` | [tests/integration/test_boundaries.py](../tests/integration/test_boundaries.py) | 0.136 | PASS |
| `test_account_limit_and_replay_at_utc_boundary` | [tests/integration/test_limits.py](../tests/integration/test_limits.py) | 0.149 | PASS |
| `test_user_limit_two_accounts_concurrently` | [tests/integration/test_limits.py](../tests/integration/test_limits.py) | 0.117 | PASS |
| `test_transfer_and_durable_replay` | [tests/integration/test_money.py](../tests/integration/test_money.py) | 0.115 | PASS |
| `test_persisted_rejection` | [tests/integration/test_money.py](../tests/integration/test_money.py) | 0.117 | PASS |
| `test_status_and_ownership[FROZEN-ACCOUNT_FROZEN]` | [tests/integration/test_money.py](../tests/integration/test_money.py) | 0.108 | PASS |
| `test_status_and_ownership[CLOSED-ACCOUNT_CLOSED]` | [tests/integration/test_money.py](../tests/integration/test_money.py) | 0.108 | PASS |
| `test_exception_rollback[BEFORE_POSTING]` | [tests/integration/test_money.py](../tests/integration/test_money.py) | 0.115 | PASS |
| `test_exception_rollback[AFTER_SOURCE_UPDATE]` | [tests/integration/test_money.py](../tests/integration/test_money.py) | 0.116 | PASS |
| `test_exception_rollback[BEFORE_LEDGER_INSERT]` | [tests/integration/test_money.py](../tests/integration/test_money.py) | 0.115 | PASS |
| `test_exception_rollback[BEFORE_SQL_COMMIT]` | [tests/integration/test_money.py](../tests/integration/test_money.py) | 0.158 | PASS |
| `test_process_kill[BEFORE_POSTING]` | [tests/integration/test_money.py](../tests/integration/test_money.py) | 0.864 | PASS |
| `test_process_kill[AFTER_SOURCE_UPDATE]` | [tests/integration/test_money.py](../tests/integration/test_money.py) | 0.804 | PASS |
| `test_process_kill[BEFORE_SQL_COMMIT]` | [tests/integration/test_money.py](../tests/integration/test_money.py) | 0.787 | PASS |
| `test_process_kill[AFTER_SQL_COMMIT_BEFORE_HTTP_RESPONSE]` | [tests/integration/test_money.py](../tests/integration/test_money.py) | 0.773 | PASS |
| `test_database_guards_and_drift_detector` | [tests/integration/test_money.py](../tests/integration/test_money.py) | 0.124 | PASS |
| `test_equal_timestamp_pages_and_tamper` | [tests/integration/test_money.py](../tests/integration/test_money.py) | 0.194 | PASS |
| `test_transfer_sequences_preserve_all_invariants` | [tests/integration/test_money.py](../tests/integration/test_money.py) | 0.439 | PASS |

## API security & operator boundaries

| Executed test case | Source | Time (s) | Result |
|---|---|---:|---|
| `test_api_contract` | [tests/security/test_api.py](../tests/security/test_api.py) | 0.286 | PASS |
| `test_bola_every_object` | [tests/security/test_api.py](../tests/security/test_api.py) | 0.157 | PASS |
| `test_refresh_reuse_and_logout` | [tests/security/test_api.py](../tests/security/test_api.py) | 0.207 | PASS |
| `test_dto_mass_assignment[amount_minor-True]` | [tests/security/test_api.py](../tests/security/test_api.py) | 0.162 | PASS |
| `test_dto_mass_assignment[amount_minor-1.0]` | [tests/security/test_api.py](../tests/security/test_api.py) | 0.169 | PASS |
| `test_dto_mass_assignment[amount_minor-1e3]` | [tests/security/test_api.py](../tests/security/test_api.py) | 0.200 | PASS |
| `test_dto_mass_assignment[amount_minor-9223372036854775808]` | [tests/security/test_api.py](../tests/security/test_api.py) | 0.147 | PASS |
| `test_dto_mass_assignment[status-COMPLETED]` | [tests/security/test_api.py](../tests/security/test_api.py) | 0.168 | PASS |
| `test_dto_mass_assignment[currency-VND]` | [tests/security/test_api.py](../tests/security/test_api.py) | 0.163 | PASS |
| `test_json_policy_request_size` | [tests/security/test_api.py](../tests/security/test_api.py) | 0.180 | PASS |
| `test_jwt_validation[expired]` | [tests/security/test_api.py](../tests/security/test_api.py) | 0.125 | PASS |
| `test_jwt_validation[issuer]` | [tests/security/test_api.py](../tests/security/test_api.py) | 0.119 | PASS |
| `test_jwt_validation[audience]` | [tests/security/test_api.py](../tests/security/test_api.py) | 0.128 | PASS |
| `test_jwt_validation[signature]` | [tests/security/test_api.py](../tests/security/test_api.py) | 0.128 | PASS |
| `test_jwt_validation[none]` | [tests/security/test_api.py](../tests/security/test_api.py) | 0.126 | PASS |
| `test_disabled_user_and_rate_limit` | [tests/security/test_api.py](../tests/security/test_api.py) | 0.675 | PASS |
| `test_trace_context_and_safe_logging` | [tests/security/test_api.py](../tests/security/test_api.py) | 0.195 | PASS |
| `test_unexpected_constraint_is_internal_not_retryable` | [tests/security/test_api.py](../tests/security/test_api.py) | 0.198 | PASS |
| `test_beneficiary_owner_and_admin_boundaries` | [tests/security/test_operations.py](../tests/security/test_operations.py) | 0.319 | PASS |

## Outbox delivery & bounded recovery

| Executed test case | Source | Time (s) | Result |
|---|---|---:|---|
| `test_pool_exhaustion_is_bounded_and_recovers` | [tests/reliability/test_pool.py](../tests/reliability/test_pool.py) | 0.250 | PASS |
| `test_two_workers_single_effect` | [tests/reliability/test_worker.py](../tests/reliability/test_worker.py) | 0.126 | PASS |
| `test_provider_failure_recovery[500]` | [tests/reliability/test_worker.py](../tests/reliability/test_worker.py) | 0.127 | PASS |
| `test_provider_failure_recovery[429]` | [tests/reliability/test_worker.py](../tests/reliability/test_worker.py) | 0.122 | PASS |
| `test_provider_failure_recovery[timeout]` | [tests/reliability/test_worker.py](../tests/reliability/test_worker.py) | 0.123 | PASS |
| `test_provider_failure_recovery[ack_loss]` | [tests/reliability/test_worker.py](../tests/reliability/test_worker.py) | 0.130 | PASS |
| `test_worker_crash_lease_expiry_dedupe` | [tests/reliability/test_worker.py](../tests/reliability/test_worker.py) | 0.115 | PASS |
| `test_bounded_dead_letter` | [tests/reliability/test_worker.py](../tests/reliability/test_worker.py) | 0.116 | PASS |
| `test_expired_lease_respects_retry_budget` | [tests/reliability/test_worker.py](../tests/reliability/test_worker.py) | 0.108 | PASS |

## Strict money types & domain boundaries

| Executed test case | Source | Time (s) | Result |
|---|---|---:|---|
| `test_strict_amount[True]` | [tests/unit/test_rules.py](../tests/unit/test_rules.py) | 0.001 | PASS |
| `test_strict_amount[False]` | [tests/unit/test_rules.py](../tests/unit/test_rules.py) | 0.000 | PASS |
| `test_strict_amount[1.0]` | [tests/unit/test_rules.py](../tests/unit/test_rules.py) | 0.000 | PASS |
| `test_strict_amount[1]` | [tests/unit/test_rules.py](../tests/unit/test_rules.py) | 0.000 | PASS |
| `test_strict_amount[0]` | [tests/unit/test_rules.py](../tests/unit/test_rules.py) | 0.000 | PASS |
| `test_strict_amount[-1]` | [tests/unit/test_rules.py](../tests/unit/test_rules.py) | 0.000 | PASS |
| `test_strict_amount[9223372036854775808]` | [tests/unit/test_rules.py](../tests/unit/test_rules.py) | 0.000 | PASS |
| `test_strict_amount[None]` | [tests/unit/test_rules.py](../tests/unit/test_rules.py) | 0.000 | PASS |
| `test_minor_unit_roundtrip` | [tests/unit/test_rules.py](../tests/unit/test_rules.py) | 0.026 | PASS |
| `test_fingerprint_scope_and_key` | [tests/unit/test_rules.py](../tests/unit/test_rules.py) | 0.000 | PASS |
| `test_database_guard` | [tests/unit/test_rules.py](../tests/unit/test_rules.py) | 0.000 | PASS |
| `test_domain_dependency_direction` | [tests/unit/test_rules.py](../tests/unit/test_rules.py) | 0.002 | PASS |
