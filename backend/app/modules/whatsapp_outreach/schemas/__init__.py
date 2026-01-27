"""
WhatsApp Outreach Schemas

Pydantic models for API request/response validation.
"""

from .whatsapp_schemas import (
    # Request schemas
    SendWhatsAppRequest,
    BulkSendWhatsAppRequest,
    CreateLeadRequest,
    UpdateLeadRequest,
    # Response schemas
    WhatsAppLeadSummary,
    WhatsAppLeadDetail,
    WhatsAppLeadsListResponse,
    WhatsAppMessageItem,
    ConversationResponse,
    SendWhatsAppResponse,
    BulkSendWhatsAppResponse,
    BulkEligibilityResponse,
    TemplateItem,
    TemplatesResponse,
    WhatsAppActivityItem,
    ActivitiesResponse,
    ImportResponse,
    WebhookResponse,
)

__all__ = [
    "SendWhatsAppRequest",
    "BulkSendWhatsAppRequest",
    "CreateLeadRequest",
    "UpdateLeadRequest",
    "WhatsAppLeadSummary",
    "WhatsAppLeadDetail",
    "WhatsAppLeadsListResponse",
    "WhatsAppMessageItem",
    "ConversationResponse",
    "SendWhatsAppResponse",
    "BulkSendWhatsAppResponse",
    "BulkEligibilityResponse",
    "TemplateItem",
    "TemplatesResponse",
    "WhatsAppActivityItem",
    "ActivitiesResponse",
    "ImportResponse",
    "WebhookResponse",
]
