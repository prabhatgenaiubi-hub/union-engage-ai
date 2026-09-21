"""Add customer email address"""
from alembic import op
import sqlalchemy as sa

revision="0011"; down_revision="0010"; branch_labels=None; depends_on=None

def upgrade():
    op.add_column("customers",sa.Column("email_address",sa.String(120),nullable=False,server_default=""))

def downgrade():
    op.drop_column("customers","email_address")
