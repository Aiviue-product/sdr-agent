"""Add WhatsApp bulk job tables

Revision ID: b7c8d9e0f1a2
Revises: 5696d32192e1
Create Date: 2026-01-26

This migration adds:
- whatsapp_bulk_jobs: Tracks bulk send jobs
- whatsapp_bulk_job_items: Individual items within a job
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b7c8d9e0f1a2'
down_revision = 'efc1ba913176'  # After: add_version_column_to_linkedin_leads
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create whatsapp_bulk_jobs table
    op.create_table(
        'whatsapp_bulk_jobs',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        
        # Job configuration
        sa.Column('template_name', sa.Text(), nullable=False),
        sa.Column('broadcast_name', sa.Text(), nullable=True),
        
        # Job status
        sa.Column('status', sa.Text(), nullable=False, server_default='pending'),
        
        # Progress tracking
        sa.Column('total_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('pending_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('sent_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failed_count', sa.Integer(), nullable=False, server_default='0'),
        
        # Error tracking
        sa.Column('error_message', sa.Text(), nullable=True),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    
    # Create indexes for bulk_jobs
    op.create_index('idx_bulk_jobs_status', 'whatsapp_bulk_jobs', ['status'])
    op.create_index('idx_bulk_jobs_created', 'whatsapp_bulk_jobs', ['created_at'])
    
    # Create whatsapp_bulk_job_items table
    op.create_table(
        'whatsapp_bulk_job_items',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        
        # Foreign keys
        sa.Column('job_id', sa.BigInteger(), 
                  sa.ForeignKey('whatsapp_bulk_jobs.id', ondelete='CASCADE'), 
                  nullable=False),
        sa.Column('lead_id', sa.BigInteger(), 
                  sa.ForeignKey('whatsapp_leads.id', ondelete='CASCADE'), 
                  nullable=False),
        
        # Item status
        sa.Column('status', sa.Text(), nullable=False, server_default='pending'),
        
        # Result tracking
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('wati_message_id', sa.Text(), nullable=True),
        
        # Timestamps
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    
    # Create indexes for bulk_job_items
    op.create_index('idx_bulk_job_items_job_id', 'whatsapp_bulk_job_items', ['job_id'])
    op.create_index('idx_bulk_job_items_status', 'whatsapp_bulk_job_items', ['status'])
    op.create_index('idx_bulk_job_items_lead_id', 'whatsapp_bulk_job_items', ['lead_id'])


def downgrade() -> None:
    # Drop indexes first
    op.drop_index('idx_bulk_job_items_lead_id', table_name='whatsapp_bulk_job_items')
    op.drop_index('idx_bulk_job_items_status', table_name='whatsapp_bulk_job_items')
    op.drop_index('idx_bulk_job_items_job_id', table_name='whatsapp_bulk_job_items')
    
    op.drop_index('idx_bulk_jobs_created', table_name='whatsapp_bulk_jobs')
    op.drop_index('idx_bulk_jobs_status', table_name='whatsapp_bulk_jobs')
    
    # Drop tables
    op.drop_table('whatsapp_bulk_job_items')
    op.drop_table('whatsapp_bulk_jobs')
