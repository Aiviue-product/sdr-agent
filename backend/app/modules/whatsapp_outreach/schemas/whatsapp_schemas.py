"""
WhatsApp Outreach - Pydantic Schemas
Request and Response models for API endpoints.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
import re


# ============================================
# REQUEST MODELS
# ============================================

class SendWhatsAppRequest(BaseModel):
    """Request to send a WhatsApp template message to a lead"""
    template_name: str = Field(
        ...,
        description="Name of the WATI template to use"
    )
    custom_params: Optional[Dict[str, str]] = Field(
        default=None,
        description="Custom parameter values to override defaults"
    )
    broadcast_name: Optional[str] = Field(
        default=None,
        description="Optional campaign/broadcast identifier"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "template_name": "test",
                "custom_params": {"name": "John"},
                "broadcast_name": "jan_2026_campaign"
            }
        }


class BulkSendWhatsAppRequest(BaseModel):
    """Request for bulk WhatsApp send"""
    lead_ids: List[int] = Field(
        ..., 
        min_length=1, 
        max_length=100,
        description="List of lead IDs to message"
    )
    template_name: str = Field(
        ...,
        description="Name of the WATI template to use"
    )
    broadcast_name: Optional[str] = Field(
        default=None,
        description="Optional campaign/broadcast identifier"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "lead_ids": [1, 2, 3],
                "template_name": "test",
                "broadcast_name": "jan_2026_bulk"
            }
        }


class CreateLeadRequest(BaseModel):
    """Request to create a new WhatsApp lead manually"""
    mobile_number: str = Field(
        ...,
        description="Mobile number (will be normalized to E.164)"
    )
    first_name: str = Field(
        ...,
        min_length=1,
        description="First name (required)"
    )
    last_name: Optional[str] = None
    email: Optional[str] = None
    company_name: Optional[str] = None
    designation: Optional[str] = None
    linkedin_url: Optional[str] = None
    sector: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "mobile_number": "919876543210",
                "first_name": "John",
                "last_name": "Doe",
                "company_name": "Acme Corp"
            }
        }

    @field_validator("mobile_number")
    @classmethod
    def validate_mobile(cls, v: str) -> str:
        # Strip common formatting
        cleaned = re.sub(r"[\s\+\-\(\)]", "", v)
        if not cleaned.isdigit():
            raise ValueError("Mobile number must contain only digits")
        if not (7 <= len(cleaned) <= 15):
            raise ValueError("Mobile number must be between 7 and 15 digits")
        return cleaned

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return v
        email_regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        if not re.match(email_regex, v):
            raise ValueError("Invalid email format")
        return v.lower().strip()

    @field_validator("linkedin_url")
    @classmethod
    def validate_linkedin(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return v
        if "linkedin.com" not in v.lower():
            raise ValueError("Invalid LinkedIn URL")
        return v.strip()


class UpdateLeadRequest(BaseModel):
    """Request to update a WhatsApp lead"""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    company_name: Optional[str] = None
    designation: Optional[str] = None
    linkedin_url: Optional[str] = None
    sector: Optional[str] = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return v
        email_regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        if not re.match(email_regex, v):
            raise ValueError("Invalid email format")
        return v.lower().strip()

    @field_validator("linkedin_url")
    @classmethod
    def validate_linkedin(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return v
        if "linkedin.com" not in v.lower():
            raise ValueError("Invalid LinkedIn URL")
        return v.strip()


# ============================================
# RESPONSE MODELS
# ============================================

class WhatsAppLeadSummary(BaseModel):
    """Summary of a lead for list view"""
    id: int
    mobile_number: str
    first_name: str
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[str] = None
    company_name: Optional[str] = None
    designation: Optional[str] = None
    linkedin_url: Optional[str] = None
    source: Optional[str] = None
    is_wa_sent: bool = False
    last_delivery_status: Optional[str] = None
    last_sent_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class WhatsAppLeadDetail(BaseModel):
    """Full lead details including message history"""
    id: int
    mobile_number: str
    first_name: str
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[str] = None
    company_name: Optional[str] = None
    designation: Optional[str] = None
    linkedin_url: Optional[str] = None
    sector: Optional[str] = None
    source: Optional[str] = None
    source_lead_id: Optional[int] = None
    is_wa_sent: bool = False
    last_sent_at: Optional[datetime] = None
    last_template_used: Optional[str] = None
    last_delivery_status: Optional[str] = None
    last_failed_reason: Optional[str] = None
    wati_contact_id: Optional[str] = None
    wati_conversation_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class WhatsAppLeadsListResponse(BaseModel):
    """Response for leads list endpoint"""
    leads: List[WhatsAppLeadSummary]
    total_count: int
    skip: int
    limit: int


class WhatsAppMessageItem(BaseModel):
    """Single message item for conversation view"""
    id: int
    whatsapp_lead_id: int
    direction: str  # outbound/inbound
    template_name: Optional[str] = None
    message_text: str
    parameters: Optional[Dict[str, Any]] = None
    status: str
    failed_reason: Optional[str] = None
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    created_at: datetime


class ConversationResponse(BaseModel):
    """Response for message history"""
    messages: List[WhatsAppMessageItem]
    total_count: int
    lead_id: int


class SendWhatsAppResponse(BaseModel):
    """Response for send WhatsApp operation"""
    success: bool
    message: str
    lead_id: int
    phone_number: Optional[str] = None
    template_name: Optional[str] = None
    status: Optional[str] = None
    error: Optional[str] = None


class BulkSendWhatsAppResponse(BaseModel):
    """Response for bulk WhatsApp operation"""
    success: bool
    broadcast_name: str
    total: int
    success_count: int
    failed_count: int
    results: List[Dict[str, Any]]


class BulkEligibilityResponse(BaseModel):
    """Response for bulk eligibility check"""
    success: bool
    eligible: List[Dict[str, Any]]
    eligible_count: int
    ineligible: List[Dict[str, Any]]
    ineligible_count: int
    total_requested: int


class TemplateItem(BaseModel):
    """Single template for dropdown/selection"""
    id: Optional[str] = None  # WATI uses MongoDB ObjectId (string)
    name: str
    category: Optional[str] = None
    body: Optional[str] = None
    params: List[str] = []
    has_header: bool = False
    has_buttons: bool = False


class TemplatesResponse(BaseModel):
    """Response for templates list"""
    success: bool
    templates: List[TemplateItem]
    total: int


class WhatsAppActivityItem(BaseModel):
    """Single activity item for timeline"""
    id: int
    whatsapp_lead_id: Optional[int] = None
    activity_type: str
    title: str
    description: Optional[str] = None
    lead_name: Optional[str] = None
    lead_mobile: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = None
    is_global: bool = False
    created_at: datetime


class ActivitiesResponse(BaseModel):
    """Response for activities list"""
    activities: List[WhatsAppActivityItem]
    total_count: int
    page: int
    limit: int
    has_more: bool


class ImportResponse(BaseModel):
    """Response for import operations"""
    success: bool
    source: str
    total_with_mobile: int
    inserted: int
    updated: int
    skipped: int
    errors: List[str] = []


class WebhookResponse(BaseModel):
    """Response for webhook processing"""
    success: bool
    event_type: Optional[str] = None
    lead_id: Optional[int] = None
    error: Optional[str] = None


# ============================================
# BULK JOB SCHEMAS
# ============================================

class BulkJobItem(BaseModel):
    """Single item in a bulk job"""
    id: int
    job_id: int
    lead_id: int
    status: str
    error_message: Optional[str] = None
    wati_message_id: Optional[str] = None
    processed_at: Optional[datetime] = None
    created_at: datetime


class BulkJobDetail(BaseModel):
    """Full bulk job details"""
    id: int
    template_name: str
    broadcast_name: Optional[str] = None
    status: str
    total_count: int
    pending_count: int
    sent_count: int
    failed_count: int
    progress_percent: float
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class BulkJobsListResponse(BaseModel):
    """Response for bulk jobs list"""
    success: bool
    jobs: List[BulkJobDetail]
    total: int
    skip: int
    limit: int


class BulkJobResponse(BaseModel):
    """Response for single bulk job operation"""
    success: bool
    job: Optional[BulkJobDetail] = None
    message: Optional[str] = None
    error: Optional[str] = None
    sent: Optional[int] = None
    failed: Optional[int] = None
    can_resume: Optional[bool] = None


class BulkJobItemsResponse(BaseModel):
    """Response for bulk job items"""
    success: bool
    items: List[BulkJobItem]
    job: Optional[BulkJobDetail] = None
    error: Optional[str] = None


class CreateBulkJobRequest(BaseModel):
    """Request to create a new bulk job"""
    lead_ids: List[int] = Field(..., min_length=1, max_length=1000)
    template_name: str
    broadcast_name: Optional[str] = None
    start_immediately: bool = Field(default=False, description="If true, starts processing right away")
