"""Create initial RunStats schema."""

from __future__ import annotations

from alembic import op

from runstats.db.models import Base

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all initial tables, indexes, and constraints."""

    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    """Drop all initial RunStats tables."""

    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
