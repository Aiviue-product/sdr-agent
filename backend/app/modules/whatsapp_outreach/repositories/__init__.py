"""
WhatsApp Outreach Repositories

Database access layer for WhatsApp outreach module.
"""

from .whatsapp_lead_repository import WhatsAppLeadRepository
from .whatsapp_message_repository import WhatsAppMessageRepository
from .whatsapp_activity_repository import WhatsAppActivityRepository

__all__ = [
    "WhatsAppLeadRepository",
    "WhatsAppMessageRepository",
    "WhatsAppActivityRepository",
]
