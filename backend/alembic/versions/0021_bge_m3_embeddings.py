"""Migrate PDF knowledge retrieval to BGE-M3 embeddings."""
from alembic import op
from pgvector.sqlalchemy import Vector

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade():
    # Existing 768-dimensional nomic vectors cannot be compared with BGE-M3's
    # 1024-dimensional vectors. Remove only uploaded PDF knowledge, then resize.
    op.execute("DELETE FROM knowledge_chunks")
    op.execute("DELETE FROM knowledge_documents")
    op.alter_column("knowledge_chunks", "embedding", existing_type=Vector(768), type_=Vector(1024), postgresql_using="embedding::vector(1024)")


def downgrade():
    op.execute("DELETE FROM knowledge_chunks")
    op.execute("DELETE FROM knowledge_documents")
    op.alter_column("knowledge_chunks", "embedding", existing_type=Vector(1024), type_=Vector(768), postgresql_using="embedding::vector(768)")
