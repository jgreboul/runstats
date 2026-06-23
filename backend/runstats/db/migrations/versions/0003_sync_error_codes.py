"""Store documented sync error codes."""

from __future__ import annotations

from alembic import op
from sqlalchemy import Column, Text, inspect

revision = "0003_sync_error_codes"
down_revision = "0002_device_settings_fit_folder"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add a safe sync error code to sync history."""

    bind = op.get_bind()
    columns = {column["name"] for column in inspect(bind).get_columns("sync_runs")}
    if "error_code" in columns:
        return

    with op.batch_alter_table("sync_runs") as batch_op:
        batch_op.add_column(Column("error_code", Text(), nullable=True))


def downgrade() -> None:
    """Remove sync error codes from sync history."""

    bind = op.get_bind()
    columns = {column["name"] for column in inspect(bind).get_columns("sync_runs")}
    if "error_code" not in columns:
        return

    with op.batch_alter_table("sync_runs") as batch_op:
        batch_op.drop_column("error_code")
