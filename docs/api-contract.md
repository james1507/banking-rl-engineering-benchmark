# API contract
Base `/api/v1`; interactive schema `/docs` in local/test. USD integer cents only.
Login: `POST /auth/login {email,password}`. Refresh/logout accept `{refresh_token}`. Refresh tokens are opaque and hashed at rest; reuse revokes entire family. Credentials read from local .env; no active public default.
All sensitive routes require `Authorization: Bearer <access_token>`.

Transfers: `POST /transfers` with `Idempotency-Key` (8–128 visible ASCII), source/destination UUIDs, positive BIGINT amount_minor, currency USD, optional reference <=140 characters. Returns 201 COMPLETED, original response on replay, 409 IDEMPOTENCY_KEY_REUSED on semantic mismatch. Insufficient/frozen/closed/currency/overflow rejection after authorized account resolution is durable. Malformed requests, missing account and unauthorized source roll back claim; corrected same-key request may proceed.
Same-account request returns 422 SAME_ACCOUNT_TRANSFER before claim. Status/actor/ledger fields are forbidden writes.

Errors: `{error:{code,message,request_id,details:{}}}`. 401 auth, 403 admin denied, 404 masked resource, 409 business conflict, 422 validation, 429 auth throttle, 503 bounded infrastructure/unknown outcome. Preserve key after 503 or transport loss.
Every response has validated/generated X-Request-ID. A replayed error body preserves original request_id; response header represents new attempt. No sensitive input reflected in validation errors.

Accounts: GET `/accounts`, `/accounts/{id}`, `/accounts/{id}/statement` owner-only. Transfers GET collection and detail allow participants; explicit admin may read details. Collection supports status, since/until with timezone and keyset paging. Statement supports since/until. `limit` 1–100; order `(created_at DESC,id DESC)`; signed cursor binds actor/account/filters and upper boundary. New keys above upper boundary excluded; backdated inserts below boundary may appear. No historical MVCC snapshot across requests is claimed.

Admin POST `/admin/reconciliation-runs` records read-only financial analysis plus audit metadata; GET by run ID returns findings. Financial repair is not exposed.
Health live checks process; ready requires DB and schema revision. Metrics available on loopback-bound local API. Public deployment requires authenticated/internal metrics ingress.
