# Measured local profile
Actual execution: 2026-11-12T02:56:59.510698+00:00. Host Apple M2 Pro/16 GiB; Docker Desktop Linux aarch64, 10 CPUs exposed/8 GiB memory. M1 and remote amd64 were not executed.

3 samples, 50 unique successful HTTP transfers each, concurrency 10, 10 warmups. One-cent synthetic operations use real API/auth/PostgreSQL. Other local core/scenario containers may share CPU; no isolated production SLO claim.

| Sample | Requests | Median ms | p95 ms |
|---|---:|---:|---:|
| 1 | 50 | 51.79 | 85.46 |
| 2 | 50 | 42.78 | 54.14 |
| 3 | 50 | 43.13 | 59.92 |

Generated 1,000 additional history transfers; final count 1163 transfers / 2326 postings. Independent reconciliation found zero discrepancies. Actual EXPLAIN before/after native ANALYZE stored in evidence/load. Fresh fixture statistics can change plan selection; no universal latency/throughput improvement is asserted.

10k/100k datasets, contention scaling, p99 reliability and production availability remain unmeasured. Deferred projection guards recompute per-account sums; profile at larger volumes before optimization. No result was extrapolated into a production claim.
