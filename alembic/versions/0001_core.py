"""Frozen initial schema; never imports mutable runtime metadata."""

from pathlib import Path
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(Path(__file__).with_suffix(".sql").read_text())


def downgrade() -> None:
    raise RuntimeError(
        "Destructive financial downgrade refused. Restore backup to a new DB; see runbook."
    )
