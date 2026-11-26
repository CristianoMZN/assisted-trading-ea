"""Create local analysis, evidence, and version tables."""

from alembic import op
import sqlalchemy as sa


revision = "0001_analysis_storage"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "analyses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("request_id", sa.String(length=64), nullable=False),
        sa.Column("logical_symbol", sa.String(length=16), nullable=False),
        sa.Column("broker_symbol", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("decision", sa.JSON(), nullable=True),
        sa.Column("reason_code", sa.String(length=96), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("request_id"),
    )
    op.create_index("ix_analyses_created_at", "analyses", ["created_at"])
    op.create_table(
        "analysis_evidence",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("analysis_id", sa.Integer(), sa.ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("evidence_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=256), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("data", sa.JSON(), nullable=True),
    )
    op.create_index("ix_analysis_evidence_analysis_id", "analysis_evidence", ["analysis_id"])
    op.create_table(
        "analysis_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("analysis_id", sa.Integer(), sa.ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("component", sa.String(length=64), nullable=False),
        sa.Column("version", sa.String(length=128), nullable=False),
        sa.Column("model_id", sa.String(length=256), nullable=True),
        sa.Column("configuration", sa.JSON(), nullable=True),
        sa.UniqueConstraint("analysis_id", "component", name="uq_analysis_versions_component"),
    )
    op.create_index("ix_analysis_versions_analysis_id", "analysis_versions", ["analysis_id"])


def downgrade() -> None:
    op.drop_index("ix_analysis_versions_analysis_id", table_name="analysis_versions")
    op.drop_table("analysis_versions")
    op.drop_index("ix_analysis_evidence_analysis_id", table_name="analysis_evidence")
    op.drop_table("analysis_evidence")
    op.drop_index("ix_analyses_created_at", table_name="analyses")
    op.drop_table("analyses")
