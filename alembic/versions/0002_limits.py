"""Optional per-account/per-user limits; additive compatible schema."""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""CREATE TABLE transfer_limits (
      subject_type text NOT NULL CHECK(subject_type IN ('ACCOUNT','USER')),
      subject_id uuid NOT NULL, daily_minor bigint NOT NULL CHECK(daily_minor>0),
      updated_at timestamptz NOT NULL DEFAULT now(), PRIMARY KEY(subject_type,subject_id));
      GRANT SELECT,INSERT,UPDATE ON transfer_limits TO lab_app;
      CREATE INDEX daily_user_transfers ON transfers(actor_user_id,created_at) INCLUDE(amount_minor) WHERE status='COMPLETED';
      CREATE INDEX daily_account_transfers ON transfers(source_account_id,created_at) INCLUDE(amount_minor) WHERE status='COMPLETED';""")


def downgrade() -> None:
    raise RuntimeError(
        "Use compatible forward migration or restore new DB; never drop limits during live writes"
    )
