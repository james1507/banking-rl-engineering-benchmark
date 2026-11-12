# Data model
Frozen SQL: alembic/versions/0001_core.sql. Runtime SQLAlchemy Account/Posting mappings are read models; schema changes only through Alembic.
Users own CUSTOMER accounts; SYSTEM treasury has no owner and may be negative. All balances start zero; funding is a completed transfer with FUNDING journal, two postings and durable idempotency. There is one treasury per currency. No API registration or treasury debit endpoint.
Transfers are inserted terminal COMPLETED/REJECTED inside one transaction; PENDING never commits in implemented synchronous path. Complete journal has exactly two postings, net zero, matching currency/source/destination/amount. Ledger/group/transfer/audit mutation is denied. Deferred triggers check groups and projection at commit.
Idempotency stores canonical request hash and original JSON outcome; no automatic archival. Outbox aggregates are unique by transfer. Inbox plus notification effect commits atomically in fake consumer.
BIGINT applies to individual balances/postings; SQL SUM returns numeric for independent aggregation without overflow. Version increments per posting.
Indexes support owner/status, actor/source/destination history, statement compound cursor, refresh family, and due outbox claims.
