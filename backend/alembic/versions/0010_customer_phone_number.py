"""Add customer phone number"""
from alembic import op
import sqlalchemy as sa

revision="0010"; down_revision="0009"; branch_labels=None; depends_on=None

def upgrade():
    op.add_column("customers",sa.Column("phone_number",sa.String(20),nullable=False,server_default=""))

def downgrade():
    op.drop_column("customers","phone_number")
