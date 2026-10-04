"""Service request internal comments"""
from alembic import op
import sqlalchemy as sa

revision="0003"; down_revision="0002"; branch_labels=None; depends_on=None

def upgrade():
    op.create_table(
        "service_request_comments",
        sa.Column("id",sa.Integer(),primary_key=True),
        sa.Column("service_request_id",sa.Integer(),sa.ForeignKey("service_requests.id"),nullable=False),
        sa.Column("author_id",sa.Integer(),sa.ForeignKey("users.id"),nullable=False),
        sa.Column("comment",sa.Text(),nullable=False),
        sa.Column("created_at",sa.DateTime(),nullable=False),
    )
    op.create_index("ix_service_request_comments_service_request_id","service_request_comments",["service_request_id"])
    op.create_index("ix_service_request_comments_author_id","service_request_comments",["author_id"])

def downgrade():
    op.drop_table("service_request_comments")
