"""Track retention-message generation and RAG sources."""
from alembic import op
import sqlalchemy as sa

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("retention_scores",sa.Column("message_generated_by",sa.String(length=60),nullable=False,server_default="Deterministic fallback"))
    op.add_column("retention_scores",sa.Column("knowledge_sources",sa.JSON(),nullable=False,server_default="[]"))


def downgrade():
    op.drop_column("retention_scores","knowledge_sources")
    op.drop_column("retention_scores","message_generated_by")
