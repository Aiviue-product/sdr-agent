"""
LinkedIn Activity ORM Model
SQLAlchemy model representing the 'linkedin_activities' table.

This table tracks all LinkedIn outreach activities for the activity timeline.
Activities include: connection requests, acceptance, DMs sent, replies received.
"""
from sqlalchemy import Column, BigInteger, Text, DateTime, Index, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.shared.db.base import Base


class LinkedInActivity(Base):
    """
    ORM Model for the linkedin_activities table.
    
    Tracks all LinkedIn outreach activities for timeline display.
    Each activity is linked to a lead and has a type and optional message.
    """
    __tablename__ = "linkedin_activities"

    # Primary Key
    id = Column(BigInteger, primary_key=True)
    
    # ============================================
    # FOREIGN KEY
    # ============================================
    lead_id = Column(BigInteger, ForeignKey('linkedin_outreach_leads.id', ondelete='CASCADE'), nullable=False)
    
    # ============================================
    # ACTIVITY DETAILS
    # ============================================
    activity_type = Column(Text, nullable=False)  
    # Types: connection_sent, connection_accepted, connection_rejected,
    #        dm_sent, dm_replied, follow_up_sent
    
    message = Column(Text, nullable=True)         # The message sent/received (optional)
    
    # ============================================
    # LEAD INFO (denormalized for timeline display)
    # ============================================
    lead_name = Column(Text, nullable=True)       # Lead's name (for quick display)
    lead_linkedin_url = Column(Text, nullable=True)  # Lead's LinkedIn URL
    
    # ============================================
    # EXTRA DATA
    # ============================================
    extra_data = Column(JSONB, nullable=True, server_default='{}')  # Extra info (provider_id, etc.)
    
    # ============================================
    # TIMESTAMPS 
    # ============================================
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # ============================================
    # INDEXES
    # ============================================
    __table_args__ = (
        Index('idx_linkedin_activities_lead_id', 'lead_id'),
        Index('idx_linkedin_activities_type', 'activity_type'),
        Index('idx_linkedin_activities_created_at', 'created_at'),
    )

    def __repr__(self):
        return f"<LinkedInActivity(id={self.id}, type='{self.activity_type}', lead_id={self.lead_id})>"
