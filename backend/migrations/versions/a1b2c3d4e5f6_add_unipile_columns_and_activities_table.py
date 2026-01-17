"""add_unipile_columns_and_activities_table

Revision ID: a1b2c3d4e5f6
Revises: c8c7442997aa
Create Date: 2026-01-17 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'c8c7442997aa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: Add Unipile integration columns and LinkedIn activities table."""
    
    # ====================================
    # ADD NEW COLUMNS TO linkedin_outreach_leads
    # ====================================
    op.add_column('linkedin_outreach_leads', 
        sa.Column('provider_id', sa.Text(), nullable=True))
    op.add_column('linkedin_outreach_leads', 
        sa.Column('connection_status', sa.Text(), server_default='none', nullable=True))
    op.add_column('linkedin_outreach_leads', 
        sa.Column('connection_sent_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('linkedin_outreach_leads', 
        sa.Column('dm_status', sa.Text(), server_default='not_sent', nullable=True))
    op.add_column('linkedin_outreach_leads', 
        sa.Column('follow_up_count', sa.BigInteger(), server_default='0', nullable=True))
    op.add_column('linkedin_outreach_leads', 
        sa.Column('next_follow_up_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('linkedin_outreach_leads', 
        sa.Column('last_reply_at', sa.DateTime(timezone=True), nullable=True))
    
    # Create indexes for new columns
    op.create_index('idx_linkedin_leads_connection_status', 'linkedin_outreach_leads', 
        ['connection_status'], unique=False)
    op.create_index('idx_linkedin_leads_provider_id', 'linkedin_outreach_leads', 
        ['provider_id'], unique=False)
    
    # ====================================
    # CREATE linkedin_activities TABLE
    # ====================================
    op.create_table('linkedin_activities',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('lead_id', sa.BigInteger(), nullable=False),
        sa.Column('activity_type', sa.Text(), nullable=False),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('lead_name', sa.Text(), nullable=True),
        sa.Column('lead_linkedin_url', sa.Text(), nullable=True),
        sa.Column('extra_data', postgresql.JSONB(astext_type=sa.Text()), 
            server_default='{}', nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), 
            server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['lead_id'], ['linkedin_outreach_leads.id'], 
            ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for activities table
    op.create_index('idx_linkedin_activities_lead_id', 'linkedin_activities', 
        ['lead_id'], unique=False)
    op.create_index('idx_linkedin_activities_type', 'linkedin_activities', 
        ['activity_type'], unique=False)
    op.create_index('idx_linkedin_activities_created_at', 'linkedin_activities', 
        ['created_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema: Remove Unipile columns and activities table."""
    
    # Drop activities table
    op.drop_index('idx_linkedin_activities_created_at', table_name='linkedin_activities')
    op.drop_index('idx_linkedin_activities_type', table_name='linkedin_activities')
    op.drop_index('idx_linkedin_activities_lead_id', table_name='linkedin_activities')
    op.drop_table('linkedin_activities')
    
    # Drop indexes from linkedin_outreach_leads
    op.drop_index('idx_linkedin_leads_provider_id', table_name='linkedin_outreach_leads')
    op.drop_index('idx_linkedin_leads_connection_status', table_name='linkedin_outreach_leads')
    
    # Drop columns from linkedin_outreach_leads
    op.drop_column('linkedin_outreach_leads', 'last_reply_at')
    op.drop_column('linkedin_outreach_leads', 'next_follow_up_at')
    op.drop_column('linkedin_outreach_leads', 'follow_up_count')
    op.drop_column('linkedin_outreach_leads', 'dm_status')
    op.drop_column('linkedin_outreach_leads', 'connection_sent_at')
    op.drop_column('linkedin_outreach_leads', 'connection_status')
    op.drop_column('linkedin_outreach_leads', 'provider_id')
