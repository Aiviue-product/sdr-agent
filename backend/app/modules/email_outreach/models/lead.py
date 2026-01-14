"""
Lead ORM Model
SQLAlchemy model representing the 'leads' table in the database.
This is the source of truth for the leads table schema.

IMPORTANT: This model matches the actual Supabase database schema exactly.
"""
from sqlalchemy import Column, BigInteger, Text, Boolean, DateTime, Index, Enum
from sqlalchemy.dialects.postgresql import JSONB
import enum
from app.shared.db.base import Base


class EnrichmentStatusEnum(enum.Enum):
    """Enum for enrichment status - matches PostgreSQL enrichment_status_enum"""
    pending = "pending"
    completed = "completed"
    failed = "failed"


class Lead(Base):
    """
    ORM Model for the leads table.
    
    This model defines the schema for storing lead/contact information
    used in email outreach campaigns.
    """
    __tablename__ = "leads"

    # Primary Key
    id = Column(BigInteger, primary_key=True)
    
    # Basic Contact Info (email and first_name are NOT NULL)
    email = Column(Text, unique=True, nullable=False)
    first_name = Column(Text, nullable=False)
    last_name = Column(Text, nullable=True)
    mobile_number = Column(Text, nullable=True)
    
    # Company Info
    company_name = Column(Text, nullable=True)
    designation = Column(Text, nullable=True)
    sector = Column(Text, nullable=True)
    linkedin_url = Column(Text, nullable=True)
    
    # Lead Management
    priority = Column(Text, nullable=True)
    lead_stage = Column(Text, nullable=True)
    
    # Email Verification (from MillionVerifier/etc)
    verification_status = Column(Text, nullable=True)
    verification_tag = Column(Text, nullable=True)
    
    # Enrichment Data (from LinkedIn scraping + AI analysis)
    enrichment_status = Column(
        Enum(EnrichmentStatusEnum, name='enrichment_status_enum', create_type=False),
        nullable=True,
        server_default='pending'
    )
    hiring_signal = Column(Boolean, nullable=True, default=False)
    ai_variables = Column(JSONB, nullable=True, server_default='{}')
    scraped_data = Column(JSONB, nullable=True, server_default='[]')
    personalized_intro = Column(Text, nullable=True)
    
    # Email Sequence (3-step campaign)
    email_1_subject = Column(Text, nullable=True)
    email_1_body = Column(Text, nullable=True)
    email_2_subject = Column(Text, nullable=True)
    email_2_body = Column(Text, nullable=True)
    email_3_subject = Column(Text, nullable=True)
    email_3_body = Column(Text, nullable=True)
    
    # Sending Status (to Instantly)
    is_sent = Column(Boolean, nullable=True, default=False)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    instantly_lead_id = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)

    # Indexes that exist in the database
    __table_args__ = (
        Index('idx_leads_status', 'verification_status', 'is_sent'),
        Index('idx_lead_stage', 'lead_stage'),
    )

    def __repr__(self):
        return f"<Lead(id={self.id}, email='{self.email}', company='{self.company_name}')>"
