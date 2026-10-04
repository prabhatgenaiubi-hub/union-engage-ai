"""Customer-visible service request messages"""
from alembic import op
import sqlalchemy as sa

revision="0004"; down_revision="0003"; branch_labels=None; depends_on=None

def upgrade():
    op.create_table(
        "service_request_messages",
        sa.Column("id",sa.Integer(),primary_key=True),
        sa.Column("service_request_id",sa.Integer(),sa.ForeignKey("service_requests.id"),nullable=False),
        sa.Column("sender_id",sa.Integer(),sa.ForeignKey("users.id"),nullable=False),
        sa.Column("sender_type",sa.String(20),nullable=False),
        sa.Column("message",sa.Text(),nullable=False),
        sa.Column("created_at",sa.DateTime(),nullable=False),
    )
    op.create_index("ix_service_request_messages_service_request_id","service_request_messages",["service_request_id"])
    op.create_index("ix_service_request_messages_sender_id","service_request_messages",["sender_id"])

def downgrade():
    op.drop_table("service_request_messages")
