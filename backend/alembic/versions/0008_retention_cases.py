"""Retention and win-back cases"""
from alembic import op
import sqlalchemy as sa

revision="0008"; down_revision="0007"; branch_labels=None; depends_on=None

def upgrade():
    op.add_column("retention_scores",sa.Column("case_type",sa.String(30),nullable=False,server_default="Retention"))
    op.add_column("retention_scores",sa.Column("status",sa.String(30),nullable=False,server_default="Monitoring"))
    op.add_column("retention_scores",sa.Column("communication_draft",sa.Text(),nullable=False,server_default=""))
    op.add_column("retention_scores",sa.Column("reviewed_by",sa.Integer(),sa.ForeignKey("users.id"),nullable=True))
    op.add_column("retention_scores",sa.Column("reviewed_at",sa.DateTime(),nullable=True))

def downgrade():
    for column in ["reviewed_at","reviewed_by","communication_draft","status","case_type"]:op.drop_column("retention_scores",column)
