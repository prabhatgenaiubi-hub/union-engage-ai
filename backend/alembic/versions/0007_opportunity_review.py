"""Reviewable personalized opportunity communication"""
from alembic import op
import sqlalchemy as sa

revision="0007"; down_revision="0006"; branch_labels=None; depends_on=None

def upgrade():
    op.add_column("product_opportunities",sa.Column("communication_draft",sa.Text(),nullable=False,server_default=""))
    op.add_column("product_opportunities",sa.Column("reviewed_by",sa.Integer(),sa.ForeignKey("users.id"),nullable=True))
    op.add_column("product_opportunities",sa.Column("reviewed_at",sa.DateTime(),nullable=True))

def downgrade():
    op.drop_column("product_opportunities","reviewed_at");op.drop_column("product_opportunities","reviewed_by");op.drop_column("product_opportunities","communication_draft")
