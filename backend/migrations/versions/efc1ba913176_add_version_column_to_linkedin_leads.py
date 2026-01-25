"""add_version_column_to_linkedin_leads

Revision ID: efc1ba913176
Revises: 9cc777bb93e0
Create Date: 2026-01-25 18:08:20.477308

This migration adds a 'version' column to the linkedin_outreach_leads table
for optimistic locking. This prevents race conditions where concurrent updates
could overwrite each other's changes.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'efc1ba913176'
down_revision: Union[str, Sequence[str], None] = '9cc777bb93e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add version column for optimistic locking."""
    # Add the version column with default value of 1
    # server_default ensures existing rows get value 1
    op.add_column(
        'linkedin_outreach_leads',
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1')
    )


def downgrade() -> None:
    """Remove version column."""
    op.drop_column('linkedin_outreach_leads', 'version')

