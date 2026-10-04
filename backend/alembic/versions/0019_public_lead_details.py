"""Capture public lead requirement details."""
from alembic import op
import sqlalchemy as sa

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("public_leads", sa.Column("requested_amount", sa.BigInteger(), nullable=True))
    op.add_column("public_leads", sa.Column("enquiry", sa.Text(), nullable=False, server_default=""))
    op.add_column("public_leads", sa.Column("details", sa.JSON(), nullable=False, server_default="{}"))


def downgrade():
    op.drop_column("public_leads", "details")
    op.drop_column("public_leads", "enquiry")
    op.drop_column("public_leads", "requested_amount")
