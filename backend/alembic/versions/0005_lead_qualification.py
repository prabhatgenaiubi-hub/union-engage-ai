"""Stateful lead qualification"""
from alembic import op
import sqlalchemy as sa

revision="0005"; down_revision="0004"; branch_labels=None; depends_on=None

def upgrade():
    op.add_column("leads",sa.Column("qualification_data",sa.JSON(),nullable=False,server_default=sa.text("'{}'::json")))
    op.add_column("leads",sa.Column("drop_off_detected",sa.Boolean(),nullable=False,server_default=sa.false()))

def downgrade():
    op.drop_column("leads","drop_off_detected");op.drop_column("leads","qualification_data")
