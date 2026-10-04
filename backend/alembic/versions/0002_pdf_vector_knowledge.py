"""PDF vector knowledge base"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
revision="0002"; down_revision="0001"; branch_labels=None; depends_on=None
def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table("knowledge_documents",sa.Column("id",sa.Integer(),primary_key=True),sa.Column("filename",sa.String(255),nullable=False),sa.Column("title",sa.String(255),nullable=False),sa.Column("sha256",sa.String(64),nullable=False),sa.Column("classification",sa.String(30),nullable=False),sa.Column("audience",sa.String(30),nullable=False),sa.Column("status",sa.String(30),nullable=False),sa.Column("page_count",sa.Integer(),nullable=False),sa.Column("chunk_count",sa.Integer(),nullable=False),sa.Column("original_file",sa.LargeBinary(),nullable=False),sa.Column("error_message",sa.Text(),nullable=True),sa.Column("uploaded_by",sa.Integer(),sa.ForeignKey("users.id"),nullable=True),sa.Column("created_at",sa.DateTime(),nullable=False),sa.Column("updated_at",sa.DateTime(),nullable=False),sa.UniqueConstraint("sha256"))
    op.create_index("ix_knowledge_documents_sha256","knowledge_documents",["sha256"],unique=True)
    op.create_index("ix_knowledge_documents_status","knowledge_documents",["status"])
    op.create_table("knowledge_chunks",sa.Column("id",sa.Integer(),primary_key=True),sa.Column("document_id",sa.Integer(),sa.ForeignKey("knowledge_documents.id"),nullable=False),sa.Column("page_number",sa.Integer(),nullable=False),sa.Column("chunk_index",sa.Integer(),nullable=False),sa.Column("content",sa.Text(),nullable=False),sa.Column("embedding",Vector(768),nullable=False))
    op.create_index("ix_knowledge_chunks_document_id","knowledge_chunks",["document_id"])
    op.create_index("ix_knowledge_chunks_page_number","knowledge_chunks",["page_number"])
def downgrade():
    op.drop_table("knowledge_chunks"); op.drop_table("knowledge_documents")
