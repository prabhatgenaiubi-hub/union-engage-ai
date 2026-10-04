from alembic import op
import sqlalchemy as sa

revision="0017"; down_revision="0016"; branch_labels=None; depends_on=None

def upgrade():
    op.add_column("public_messages",sa.Column("sources",sa.JSON(),nullable=False,server_default="[]"))

def downgrade():
    op.drop_column("public_messages","sources")
