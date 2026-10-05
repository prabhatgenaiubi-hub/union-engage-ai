"""Persist the admin-selected chat reply model."""
from alembic import op
import sqlalchemy as sa

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("app_settings",sa.Column("key",sa.String(length=80),primary_key=True),sa.Column("value",sa.String(length=120),nullable=False),sa.Column("created_at",sa.DateTime(),nullable=False),sa.Column("updated_at",sa.DateTime(),nullable=False))

def downgrade():
    op.drop_table("app_settings")
