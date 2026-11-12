CREATE TABLE users (
 id uuid PRIMARY KEY, email varchar(320) NOT NULL UNIQUE CHECK(email=lower(email)),
 password_hash text NOT NULL, role text NOT NULL DEFAULT 'USER' CHECK(role IN ('USER','ADMIN')),
 status text NOT NULL DEFAULT 'ACTIVE' CHECK(status IN ('ACTIVE','DISABLED')),
 created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE refresh_sessions (
 id uuid PRIMARY KEY, user_id uuid NOT NULL REFERENCES users, token_hash char(64) NOT NULL UNIQUE,
 family_id uuid NOT NULL, issued_at timestamptz NOT NULL, expires_at timestamptz NOT NULL,
 rotated_at timestamptz, revoked_at timestamptz, replaced_by uuid REFERENCES refresh_sessions DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX refresh_family ON refresh_sessions(family_id);
CREATE TABLE login_buckets (bucket char(64) PRIMARY KEY, attempts integer NOT NULL, reset_at timestamptz NOT NULL);
CREATE TABLE accounts (
 id uuid PRIMARY KEY, owner_user_id uuid REFERENCES users,
 account_type text NOT NULL CHECK(account_type IN ('CUSTOMER','SYSTEM')),
 currency char(3) NOT NULL CHECK(currency ~ '^[A-Z]{3}$'),
 status text NOT NULL DEFAULT 'ACTIVE' CHECK(status IN ('ACTIVE','FROZEN','CLOSED')),
 balance_minor bigint NOT NULL DEFAULT 0, version bigint NOT NULL DEFAULT 0,
 created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(),
 CHECK(account_type <> 'CUSTOMER' OR balance_minor >= 0),
 CHECK((account_type='SYSTEM' AND owner_user_id IS NULL) OR (account_type='CUSTOMER' AND owner_user_id IS NOT NULL))
);
CREATE UNIQUE INDEX one_treasury_per_currency ON accounts(currency) WHERE account_type='SYSTEM';
CREATE INDEX account_owner_status ON accounts(owner_user_id,status);
CREATE TABLE journal_groups (
 id uuid PRIMARY KEY, operation_type text NOT NULL CHECK(operation_type IN ('TRANSFER','FUNDING')),
 business_reference_id uuid NOT NULL UNIQUE, currency char(3) NOT NULL,
 posted_at timestamptz NOT NULL, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE idempotency_records (
 id uuid PRIMARY KEY, actor_user_id uuid NOT NULL REFERENCES users, operation_type text NOT NULL,
 key varchar(128) NOT NULL CHECK(length(key) BETWEEN 8 AND 128), request_hash char(64) NOT NULL,
 status text NOT NULL CHECK(status IN ('IN_PROGRESS','FINALIZED')),
 response_status integer, response_body jsonb, transfer_id uuid,
 created_at timestamptz NOT NULL, finalized_at timestamptz, expires_at timestamptz NOT NULL,
 UNIQUE(actor_user_id,operation_type,key),
 CHECK(status<>'FINALIZED' OR (response_status IS NOT NULL AND response_body IS NOT NULL AND finalized_at IS NOT NULL))
);
CREATE TABLE transfers (
 id uuid PRIMARY KEY, actor_user_id uuid NOT NULL REFERENCES users,
 source_account_id uuid NOT NULL REFERENCES accounts, destination_account_id uuid NOT NULL REFERENCES accounts,
 currency char(3) NOT NULL, amount_minor bigint NOT NULL CHECK(amount_minor>0),
 status text NOT NULL CHECK(status IN ('PENDING','COMPLETED','REJECTED')), rejection_code text,
 journal_group_id uuid UNIQUE REFERENCES journal_groups,
 idempotency_record_id uuid NOT NULL UNIQUE REFERENCES idempotency_records,
 created_at timestamptz NOT NULL, completed_at timestamptz, request_id varchar(128) NOT NULL,
 reference varchar(140),
 CHECK(source_account_id<>destination_account_id),
 CHECK((status='COMPLETED' AND journal_group_id IS NOT NULL AND completed_at IS NOT NULL AND rejection_code IS NULL)
    OR (status='REJECTED' AND journal_group_id IS NULL AND rejection_code IS NOT NULL AND completed_at IS NULL)
    OR (status='PENDING' AND journal_group_id IS NULL))
);
ALTER TABLE idempotency_records ADD CONSTRAINT idempotency_transfer_fk FOREIGN KEY(transfer_id) REFERENCES transfers DEFERRABLE INITIALLY DEFERRED;
CREATE INDEX transfer_actor_history ON transfers(actor_user_id,created_at DESC,id DESC);
CREATE INDEX transfer_source_history ON transfers(source_account_id,created_at DESC,id DESC);
CREATE INDEX transfer_destination_history ON transfers(destination_account_id,created_at DESC,id DESC);
CREATE TABLE ledger_postings (
 id uuid PRIMARY KEY, journal_group_id uuid NOT NULL REFERENCES journal_groups,
 account_id uuid NOT NULL REFERENCES accounts, currency char(3) NOT NULL,
 signed_amount_minor bigint NOT NULL CHECK(signed_amount_minor<>0),
 created_at timestamptz NOT NULL, entry_sequence smallint NOT NULL CHECK(entry_sequence IN (1,2)),
 UNIQUE(journal_group_id,entry_sequence)
);
CREATE INDEX ledger_account_history ON ledger_postings(account_id,created_at DESC,id DESC);
CREATE TABLE outbox_events (
 id uuid PRIMARY KEY, event_type text NOT NULL, aggregate_id uuid NOT NULL UNIQUE REFERENCES transfers,
 payload_json jsonb NOT NULL, status text NOT NULL DEFAULT 'PENDING' CHECK(status IN ('PENDING','LEASED','PUBLISHED','DEAD')),
 attempt_count integer NOT NULL DEFAULT 0, available_at timestamptz NOT NULL,
 leased_until timestamptz, lease_token uuid, created_at timestamptz NOT NULL,
 published_at timestamptz, last_error_code text
);
CREATE INDEX outbox_due ON outbox_events(available_at,created_at) WHERE status IN ('PENDING','LEASED');
CREATE TABLE inbox_receipts (event_id uuid NOT NULL REFERENCES outbox_events, consumer_name text NOT NULL, processed_at timestamptz NOT NULL, PRIMARY KEY(event_id,consumer_name));
CREATE TABLE notification_effects (event_id uuid PRIMARY KEY REFERENCES outbox_events, created_at timestamptz NOT NULL);
CREATE TABLE audit_events (
 id uuid PRIMARY KEY, actor_user_id uuid REFERENCES users, action text NOT NULL,
 entity_id uuid, outcome text NOT NULL, request_id text NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now(), safe_context_json jsonb NOT NULL DEFAULT '{}'
);
CREATE INDEX audit_history ON audit_events(created_at DESC,id DESC);
CREATE TABLE reconciliation_runs (id uuid PRIMARY KEY, started_at timestamptz NOT NULL, ended_at timestamptz NOT NULL, status text NOT NULL, report jsonb NOT NULL);
CREATE TABLE beneficiaries (id uuid PRIMARY KEY, owner_user_id uuid NOT NULL REFERENCES users, target_account_id uuid NOT NULL REFERENCES accounts, alias varchar(80) NOT NULL, status text NOT NULL DEFAULT 'ACTIVE' CHECK(status IN ('ACTIVE','DISABLED')), created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(owner_user_id,target_account_id));

CREATE FUNCTION deny_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Immutable financial/audit record' USING ERRCODE='23514'; END $$;
CREATE TRIGGER immutable_postings BEFORE UPDATE OR DELETE ON ledger_postings FOR EACH ROW EXECUTE FUNCTION deny_mutation();
CREATE TRIGGER immutable_journals BEFORE UPDATE OR DELETE ON journal_groups FOR EACH ROW EXECUTE FUNCTION deny_mutation();
CREATE TRIGGER immutable_audit BEFORE UPDATE OR DELETE ON audit_events FOR EACH ROW EXECUTE FUNCTION deny_mutation();
CREATE TRIGGER immutable_transfers BEFORE UPDATE OR DELETE ON transfers FOR EACH ROW EXECUTE FUNCTION deny_mutation();

CREATE FUNCTION validate_journal() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE gid uuid; n integer; total numeric; mismatch integer;
BEGIN
 IF TG_TABLE_NAME='journal_groups' THEN gid:=NEW.id; ELSE gid:=NEW.journal_group_id; END IF;
 SELECT count(*),coalesce(sum(p.signed_amount_minor),0),count(*) FILTER(WHERE p.currency<>g.currency OR p.currency<>a.currency)
 INTO n,total,mismatch FROM ledger_postings p JOIN journal_groups g ON g.id=p.journal_group_id JOIN accounts a ON a.id=p.account_id WHERE g.id=gid;
 IF n<>2 OR total<>0 OR mismatch<>0 THEN RAISE EXCEPTION 'Unbalanced journal %',gid USING ERRCODE='23514'; END IF;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER balanced_group AFTER INSERT ON journal_groups DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION validate_journal();
CREATE CONSTRAINT TRIGGER balanced_posting AFTER INSERT ON ledger_postings DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION validate_journal();
CREATE FUNCTION validate_projection() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE actual numeric; expected bigint; aid uuid;
BEGIN
 IF TG_TABLE_NAME='accounts' THEN aid:=NEW.id; ELSE aid:=NEW.account_id; END IF;
 SELECT balance_minor INTO expected FROM accounts WHERE id=aid;
 SELECT coalesce(sum(signed_amount_minor),0) INTO actual FROM ledger_postings WHERE account_id=aid;
 IF expected<>actual THEN RAISE EXCEPTION 'Account projection mismatch %',aid USING ERRCODE='23514'; END IF;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER account_projection AFTER INSERT OR UPDATE ON accounts DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION validate_projection();
CREATE CONSTRAINT TRIGGER posting_projection AFTER INSERT ON ledger_postings DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION validate_projection();
CREATE FUNCTION validate_transfer() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE n integer;
BEGIN
 IF NEW.status='COMPLETED' THEN
  SELECT count(*) INTO n FROM ledger_postings p JOIN journal_groups g ON g.id=p.journal_group_id
   WHERE g.id=NEW.journal_group_id AND g.business_reference_id=NEW.id AND g.currency=NEW.currency
   AND ((p.account_id=NEW.source_account_id AND p.signed_amount_minor=-NEW.amount_minor) OR (p.account_id=NEW.destination_account_id AND p.signed_amount_minor=NEW.amount_minor));
  IF n<>2 OR NOT EXISTS(SELECT 1 FROM outbox_events WHERE aggregate_id=NEW.id) THEN
   RAISE EXCEPTION 'Transfer journal/outbox mismatch' USING ERRCODE='23514'; END IF;
 END IF;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER complete_transfer AFTER INSERT ON transfers DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION validate_transfer();
GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO lab_app;
REVOKE UPDATE,DELETE ON ledger_postings,journal_groups,audit_events,transfers,reconciliation_runs FROM lab_app;
REVOKE ALL ON FUNCTION deny_mutation(),validate_journal(),validate_projection(),validate_transfer() FROM PUBLIC;
