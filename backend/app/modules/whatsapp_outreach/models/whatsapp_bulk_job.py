"""
WhatsApp Bulk Job ORM Models
SQLAlchemy models for tracking bulk send jobs.

This enables:
- Resuming jobs after server crash
- Progress tracking for long-running bulk sends
- Job history and analytics
"""
from sqlalchemy import Column, BigInteger, Text, Integer, DateTime, Index, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.shared.db.base import Base


class WhatsAppBulkJob(Base):
    """
    ORM Model for bulk send jobs.
    
    Tracks the overall status of a bulk send operation.
    Each job contains multiple items (one per lead).
    """
    __tablename__ = "whatsapp_bulk_jobs"

    # Primary Key
    id = Column(BigInteger, primary_key=True)
    
    # ============================================
    # JOB CONFIGURATION
    # ============================================
    template_name = Column(Text, nullable=False)
    broadcast_name = Column(Text, nullable=True)
    
    # ============================================
    # JOB STATUS
    # ============================================
    # Status: pending, running, paused, completed, failed, cancelled
    status = Column(Text, nullable=False, default='pending')
    
    # ============================================
    # PROGRESS TRACKING
    # ============================================
    total_count = Column(Integer, nullable=False, default=0)
    pending_count = Column(Integer, nullable=False, default=0)
    sent_count = Column(Integer, nullable=False, default=0)
    failed_count = Column(Integer, nullable=False, default=0)
    
    # ============================================
    # ERROR TRACKING
    # ============================================
    error_message = Column(Text, nullable=True)  # If job failed
    
    # ============================================
    # TIMESTAMPS
    # ============================================
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # ============================================
    # INDEXES
    # ============================================
    __table_args__ = (
        Index('idx_bulk_jobs_status', 'status'),
        Index('idx_bulk_jobs_created', 'created_at'),
    )

    def __repr__(self):
        return f"<WhatsAppBulkJob(id={self.id}, status='{self.status}', sent={self.sent_count}/{self.total_count})>"


class WhatsAppBulkJobItem(Base):
    """
    ORM Model for individual items within a bulk job.
    
    Each item represents a single lead to message.
    Allows tracking and resuming at the item level.
    """
    __tablename__ = "whatsapp_bulk_job_items"

    # Primary Key
    id = Column(BigInteger, primary_key=True)
    
    # ============================================
    # FOREIGN KEYS
    # ============================================
    job_id = Column(
        BigInteger, 
        ForeignKey('whatsapp_bulk_jobs.id', ondelete='CASCADE'), 
        nullable=False
    )
    lead_id = Column(
        BigInteger, 
        ForeignKey('whatsapp_leads.id', ondelete='CASCADE'), 
        nullable=False
    )
    
    # ============================================
    # ITEM STATUS
    # ============================================
    # Status: pending, processing, sent, failed, skipped
    status = Column(Text, nullable=False, default='pending')
    
    # ============================================
    # RESULT TRACKING
    # ============================================
    error_message = Column(Text, nullable=True)
    wati_message_id = Column(Text, nullable=True)
    
    # ============================================
    # TIMESTAMPS
    # ============================================
    processed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # ============================================
    # INDEXES
    # ============================================
    __table_args__ = (
        Index('idx_bulk_job_items_job_id', 'job_id'),
        Index('idx_bulk_job_items_status', 'status'),
        Index('idx_bulk_job_items_lead_id', 'lead_id'),
    )

    def __repr__(self):
        return f"<WhatsAppBulkJobItem(id={self.id}, job_id={self.job_id}, lead_id={self.lead_id}, status='{self.status}')>"
