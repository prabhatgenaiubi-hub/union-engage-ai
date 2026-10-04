from alembic import op
import sqlalchemy as sa

revision="0012"; down_revision="0011"; branch_labels=None; depends_on=None

def upgrade():
    op.add_column("product_opportunities",sa.Column("generated_by",sa.String(length=40),nullable=False,server_default="rules"))

def downgrade():
    op.drop_column("product_opportunities","generated_by")
