"""Store the optional description supplied by a service-request customer."""
from alembic import op
import sqlalchemy as sa

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("service_requests", sa.Column("customer_description", sa.Text(), nullable=False, server_default=""))

def downgrade():
    op.drop_column("service_requests", "customer_description")
