from alembic import op
import sqlalchemy as sa

revision="0013"; down_revision="0012"; branch_labels=None; depends_on=None

def upgrade():
    op.add_column("routing_decisions",sa.Column("routed_department",sa.String(length=80),nullable=False,server_default=""))
    op.add_column("routing_decisions",sa.Column("admin_comment",sa.Text(),nullable=False,server_default=""))

def downgrade():
    op.drop_column("routing_decisions","admin_comment")
    op.drop_column("routing_decisions","routed_department")
