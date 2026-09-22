from alembic import op
import sqlalchemy as sa

revision="0016"; down_revision="0015"; branch_labels=None; depends_on=None

def upgrade():
    op.create_table("public_conversations",
        sa.Column("id",sa.Integer(),primary_key=True),
        sa.Column("session_token",sa.String(64),nullable=False),
        sa.Column("title",sa.String(160),nullable=False),
        sa.Column("pending_product",sa.String(60),nullable=False),
        sa.Column("pending_question",sa.Text(),nullable=False),
        sa.Column("contact_step",sa.String(20),nullable=False),
        sa.Column("contact_name",sa.String(100),nullable=False),
        sa.Column("contact_phone",sa.String(20),nullable=False),
        sa.Column("contact_email",sa.String(120),nullable=False),
        sa.Column("created_at",sa.DateTime(),nullable=False),
        sa.Column("updated_at",sa.DateTime(),nullable=False),
    )
    op.create_index("ix_public_conversations_session_token","public_conversations",["session_token"],unique=True)
    op.create_table("public_messages",
        sa.Column("id",sa.Integer(),primary_key=True),
        sa.Column("conversation_id",sa.Integer(),sa.ForeignKey("public_conversations.id"),nullable=False),
        sa.Column("role",sa.String(20),nullable=False),
        sa.Column("content",sa.Text(),nullable=False),
        sa.Column("created_at",sa.DateTime(),nullable=False),
    )
    op.create_index("ix_public_messages_conversation_id","public_messages",["conversation_id"])
    op.create_table("public_leads",
        sa.Column("id",sa.Integer(),primary_key=True),
        sa.Column("conversation_id",sa.Integer(),sa.ForeignKey("public_conversations.id"),nullable=False),
        sa.Column("product",sa.String(60),nullable=False),
        sa.Column("name",sa.String(100),nullable=False),
        sa.Column("phone",sa.String(20),nullable=False),
        sa.Column("email",sa.String(120),nullable=False),
        sa.Column("status",sa.String(30),nullable=False),
        sa.Column("source",sa.String(40),nullable=False),
        sa.Column("created_at",sa.DateTime(),nullable=False),
        sa.Column("updated_at",sa.DateTime(),nullable=False),
    )
    op.create_index("ix_public_leads_conversation_id","public_leads",["conversation_id"],unique=True)

def downgrade():
    op.drop_table("public_leads")
    op.drop_table("public_messages")
    op.drop_table("public_conversations")
