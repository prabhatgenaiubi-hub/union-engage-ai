from alembic import op
import sqlalchemy as sa

revision="0015"; down_revision="0014"; branch_labels=None; depends_on=None

def upgrade():
    for column in ["reason","trigger","suggested_action","communication_draft"]:
        op.alter_column("product_opportunities",column,existing_type=sa.String(),type_=sa.Text(),existing_nullable=False)

def downgrade():
    op.alter_column("product_opportunities","reason",existing_type=sa.Text(),type_=sa.String(length=100),existing_nullable=False)
    op.alter_column("product_opportunities","trigger",existing_type=sa.Text(),type_=sa.String(length=100),existing_nullable=False)
    op.alter_column("product_opportunities","suggested_action",existing_type=sa.Text(),type_=sa.String(length=160),existing_nullable=False)
    op.alter_column("product_opportunities","communication_draft",existing_type=sa.Text(),type_=sa.String(length=100),existing_nullable=False)
