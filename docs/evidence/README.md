# Evidence index
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
