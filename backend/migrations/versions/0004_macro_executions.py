"""Store immutable macro refresh results without altering previous analyses."""

from alembic import op
import sqlalchemy as sa


revision = "0004_macro_executions"
down_revision = "0003_analysis_snapshot"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "macro_executions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("logical_symbol", sa.String(length=16), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("items", sa.JSON(), nullable=True),
        sa.Column("rss_evidence", sa.JSON(), nullable=True),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("model_id", sa.String(length=256), nullable=True),
        sa.Column("prompt_version", sa.String(length=128), nullable=True),
        sa.Column("error_code", sa.String(length=96), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
    )
    op.create_index("ix_macro_executions_lookup", "macro_executions", ["logical_symbol", "state", "completed_at"])


def downgrade() -> None:
    op.drop_index("ix_macro_executions_lookup", table_name="macro_executions")
    op.drop_table("macro_executions")
