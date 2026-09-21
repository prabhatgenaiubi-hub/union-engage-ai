"""Operational service routing intelligence"""
from alembic import op
import sqlalchemy as sa

revision="0009"; down_revision="0008"; branch_labels=None; depends_on=None

def upgrade():
    op.add_column("service_requests",sa.Column("assigned_queue",sa.String(50),nullable=False,server_default="Standard Queue"))
    op.add_column("service_requests",sa.Column("escalation_level",sa.String(30),nullable=False,server_default="None"))
    op.add_column("service_requests",sa.Column("routing_reason",sa.Text(),nullable=False,server_default=""))
    op.add_column("routing_decisions",sa.Column("interaction_analysis_id",sa.Integer(),sa.ForeignKey("interaction_analysis.id"),nullable=True))
    op.create_index("ix_routing_decisions_interaction_analysis_id","routing_decisions",["interaction_analysis_id"])
    op.add_column("routing_decisions",sa.Column("issue",sa.String(80),nullable=False,server_default="General service"))
    op.add_column("routing_decisions",sa.Column("urgency",sa.String(20),nullable=False,server_default="Low"))
    op.add_column("routing_decisions",sa.Column("sentiment",sa.String(30),nullable=False,server_default="Neutral"))
    op.add_column("routing_decisions",sa.Column("repeat_contact",sa.Boolean(),nullable=False,server_default=sa.false()))
    op.add_column("routing_decisions",sa.Column("escalation",sa.String(30),nullable=False,server_default="None"))
    op.add_column("routing_decisions",sa.Column("service_request_id",sa.Integer(),sa.ForeignKey("service_requests.id"),nullable=True))
    op.add_column("routing_decisions",sa.Column("actioned_by",sa.Integer(),sa.ForeignKey("users.id"),nullable=True))
    op.add_column("routing_decisions",sa.Column("actioned_at",sa.DateTime(),nullable=True))

def downgrade():
    for column in ["actioned_at","actioned_by","service_request_id","escalation","repeat_contact","sentiment","urgency","issue"]:op.drop_column("routing_decisions",column)
    op.drop_index("ix_routing_decisions_interaction_analysis_id",table_name="routing_decisions")
    op.drop_column("routing_decisions","interaction_analysis_id")
    for column in ["routing_reason","escalation_level","assigned_queue"]:op.drop_column("service_requests",column)
