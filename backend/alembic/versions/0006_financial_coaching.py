"""Stateful financial coaching plans"""
from alembic import op
import sqlalchemy as sa

revision="0006"; down_revision="0005"; branch_labels=None; depends_on=None

def upgrade():
    op.add_column("financial_goals",sa.Column("conversation_id",sa.Integer(),sa.ForeignKey("conversations.id"),nullable=True))
    op.add_column("financial_goals",sa.Column("monthly_income",sa.Float(),nullable=False,server_default="0"))
    op.add_column("financial_goals",sa.Column("monthly_expenses",sa.Float(),nullable=False,server_default="0"))
    op.add_column("financial_goals",sa.Column("status",sa.String(30),nullable=False,server_default="Planning"))
    op.add_column("financial_goals",sa.Column("coaching_plan",sa.JSON(),nullable=False,server_default=sa.text("'{}'::json")))
    op.create_index("ix_financial_goals_conversation_id","financial_goals",["conversation_id"])

def downgrade():
    op.drop_index("ix_financial_goals_conversation_id",table_name="financial_goals")
    for column in ["coaching_plan","status","monthly_expenses","monthly_income","conversation_id"]:op.drop_column("financial_goals",column)
