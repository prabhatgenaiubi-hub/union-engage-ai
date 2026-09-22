"""Remember visitors who decline optional contact collection."""
from alembic import op
import sqlalchemy as sa

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("public_conversations", sa.Column("contact_declined", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade():
    op.drop_column("public_conversations", "contact_declined")
