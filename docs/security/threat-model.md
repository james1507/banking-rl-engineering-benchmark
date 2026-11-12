# Threat model
Synthetic balances, ledger integrity, password hashes, tokens, local secrets and verifier results are assets.

| Boundary/threat | Implemented control | Limit |
|---|---|---|
| Public API / BOLA | Source-owner authorization in posting service; owner-scoped account/statement; participant transfer reads | UUID secrecy is not authorization |
| Input / mass assignment | Pydantic extra=forbid, strict BIGINT integer, 64 KiB cap, duplicate JSON key rejection | Proxy body/header limits still needed for public deployment |
| JWT / refresh replay | Algorithm/issuer/audience/expiry checks, DB user status; Argon2id; hashed rotating refresh families locked per user | Bearer access token survives logout up to 15 min; no MFA |
| Login abuse | PostgreSQL per-email 5-min attempt bucket; generic errors and dummy hash | Needs trusted-IP/edge limits and account recovery policy for public service |
| SQL / ledger mutation | Bound parameters; runtime non-owner role; UPDATE/DELETE denied; immutable/deferred triggers | Owner/migration role can override guards; keep away from API |
| Cursor injection | HMAC signature, length cap, UUID/time parsing, actor/account/filter binding | Logical key boundary is not historical MVCC snapshot |
| Logs / secrets | Allowlisted fields; never log bodies/tokens/passwords; SQL hide_parameters | Infrastructure/exception logging must preserve policy |
| Fault injection | No crash HTTP endpoint; test adapter only on isolated network; service callback requires test + disposable URL | Test adapter is intentionally not deployment artifact |
| Candidate / verifier | Separate containers, read-only source, separate code/credentials, cap-drop, no-new-privileges, no Docker socket/internet, per-run PG | Docker shares host kernel; use disposable VM for hostile arbitrary code; public solutions not secret |
| Seed/reset | Loopback allowlist; random .env secrets; reset requires exact confirmation phrase | Local admins retain ownership; do not publish .env |
| CI prompt/code injection | No pull_request_target, contents:read, no deployment credentials | Hosted CI has not yet run for this local repo |

Admin may investigate and run reconciliation; no endpoint rewrites money. Registration omitted; local seed creates synthetic users only.
