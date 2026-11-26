"""Persist the validated request snapshot with each analysis."""

from alembic import op
import sqlalchemy as sa


revision = "0003_analysis_snapshot"
down_revision = "0002_provider_credentials"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("analyses", sa.Column("request_snapshot", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("analyses", "request_snapshot")
