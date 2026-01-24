"""
WhatsApp Message ORM Model
SQLAlchemy model representing the 'whatsapp_messages' table.

This table stores the full message history for each WhatsApp lead.
Tracks both outbound (sent by us) and inbound (replies from leads) messages.
"""
from sqlalchemy import Column, BigInteger, Text, DateTime, Index, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.shared.db.base import Base


class WhatsAppMessage(Base):
    """
    ORM Model for the whatsapp_messages table.
    
    Stores full conversation history per lead.
    Each message has a direction (outbound/inbound) and status tracking.
    """
    __tablename__ = "whatsapp_messages"

    # Primary Key
    id = Column(BigInteger, primary_key=True)
    
    # ============================================
    # FOREIGN KEY TO LEAD
    # ============================================
    whatsapp_lead_id = Column(
        BigInteger, 
        ForeignKey('whatsapp_leads.id', ondelete='CASCADE'), 
        nullable=False
    )
    
    # ============================================
    # MESSAGE DIRECTION
    # ============================================
    direction = Column(Text, nullable=False)  # 'outbound' (we sent) or 'inbound' (lead replied)
    
    # ============================================
    # MESSAGE CONTENT
    # ============================================
    template_name = Column(Text, nullable=True)              # Template used (for outbound templates)
    message_text = Column(Text, nullable=False)              # Final rendered message text
    parameters = Column(JSONB, nullable=True, server_default='{}')  # Template params used
    
    # ============================================
    # DELIVERY STATUS
    # ============================================
    status = Column(Text, nullable=False, default='PENDING')  # PENDING/SENT/DELIVERED/READ/FAILED
    failed_reason = Column(Text, nullable=True)               # Error message if failed
    
    # ============================================
    # WATI MESSAGE TRACKING
    # ============================================
    wati_message_id = Column(Text, nullable=True)             # WATI's message ID (for webhook matching)
    wati_conversation_id = Column(Text, nullable=True)        # Conversation thread ID
    broadcast_name = Column(Text, nullable=True)              # Broadcast/campaign name used
    
    # ============================================
    # TIMESTAMPS
    # ============================================
    sent_at = Column(DateTime(timezone=True), nullable=True)       # When message was sent
    delivered_at = Column(DateTime(timezone=True), nullable=True)  # When delivered
    read_at = Column(DateTime(timezone=True), nullable=True)       # When read
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # ============================================
    # INDEXES
    # ============================================
    __table_args__ = (
        Index('idx_whatsapp_messages_lead_id', 'whatsapp_lead_id'),
        Index('idx_whatsapp_messages_direction', 'direction'),
        Index('idx_whatsapp_messages_status', 'status'),
        Index('idx_whatsapp_messages_wati_id', 'wati_message_id'),
        Index('idx_whatsapp_messages_created', 'created_at'),
    )

    def __repr__(self):
        return f"<WhatsAppMessage(id={self.id}, lead_id={self.whatsapp_lead_id}, direction='{self.direction}', status='{self.status}')>"
