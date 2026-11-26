"""Add encrypted provider credential storage."""

from alembic import op
import sqlalchemy as sa


revision = "0002_provider_credentials"
down_revision = "0001_analysis_storage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "provider_credentials",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("encrypted_secret", sa.LargeBinary(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("provider"),
    )


def downgrade() -> None:
    op.drop_table("provider_credentials")
