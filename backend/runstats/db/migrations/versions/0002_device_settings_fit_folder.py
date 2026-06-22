"""Add historical FIT folder to device settings."""

from __future__ import annotations

from alembic import op
from sqlalchemy import Column, Text, inspect

revision = "0002_device_settings_fit_folder"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Store the optional historical FIT import folder per device."""

    bind = op.get_bind()
    columns = {
        column["name"] for column in inspect(bind).get_columns("device_settings")
    }
    if "historical_fit_import_folder" in columns:
        return

    with op.batch_alter_table("device_settings") as batch_op:
        batch_op.add_column(
            Column("historical_fit_import_folder", Text(), nullable=True)
        )


def downgrade() -> None:
    """Remove the historical FIT import folder column."""

    bind = op.get_bind()
    columns = {
        column["name"] for column in inspect(bind).get_columns("device_settings")
    }
    if "historical_fit_import_folder" not in columns:
        return

    with op.batch_alter_table("device_settings") as batch_op:
        batch_op.drop_column("historical_fit_import_folder")
