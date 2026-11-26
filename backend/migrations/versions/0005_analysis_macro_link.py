"""Link each online analysis to its immutable macro context."""

from alembic import op
import sqlalchemy as sa


revision = "0005_analysis_macro_link"
down_revision = "0004_macro_executions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("analyses") as batch_op:
        batch_op.add_column(sa.Column("macro_execution_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key("fk_analyses_macro_execution_id", "macro_executions", ["macro_execution_id"], ["id"])


def downgrade() -> None:
    with op.batch_alter_table("analyses") as batch_op:
        batch_op.drop_constraint("fk_analyses_macro_execution_id", type_="foreignkey")
        batch_op.drop_column("macro_execution_id")
