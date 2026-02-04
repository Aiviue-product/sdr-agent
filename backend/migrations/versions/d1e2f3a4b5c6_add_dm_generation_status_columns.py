"""Add DM generation status columns for background processing

Revision ID: d1e2f3a4b5c6
Revises: 551fd77e4215
Create Date: 2026-02-04

This migration adds:
- dm_generation_status: Text column (pending/generated/failed) for tracking AI DM generation
- dm_generation_started_at: Timestamp for stuck detection

Also backfills existing leads:
- If linkedin_dm IS NOT NULL → status = 'generated'
- If linkedin_dm IS NULL → status = 'pending'
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd1e2f3a4b5c6'
down_revision: Union[str, Sequence[str], None] = '551fd77e4215'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Step 1: Add dm_generation_status column as Text with default 'pending'
    op.add_column(
        'linkedin_outreach_leads',
        sa.Column(
            'dm_generation_status',
            sa.Text(),
            nullable=False,
            server_default='pending'
        )
    )
    
    # Step 2: Add dm_generation_started_at column
    op.add_column(
        'linkedin_outreach_leads',
        sa.Column(
            'dm_generation_started_at',
            sa.DateTime(timezone=True),
            nullable=True
        )
    )
    
    # Step 3: Create index for efficient querying of pending leads
    op.create_index(
        'idx_linkedin_leads_dm_gen_status',
        'linkedin_outreach_leads',
        ['dm_generation_status']
    )
    
    # Step 4: Backfill existing leads - set status to 'generated' if linkedin_dm is not null
    op.execute("""
        UPDATE linkedin_outreach_leads 
        SET dm_generation_status = 'generated' 
        WHERE linkedin_dm IS NOT NULL
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop index
    op.drop_index('idx_linkedin_leads_dm_gen_status', table_name='linkedin_outreach_leads')
    
    # Drop columns
    op.drop_column('linkedin_outreach_leads', 'dm_generation_started_at')
    op.drop_column('linkedin_outreach_leads', 'dm_generation_status')
