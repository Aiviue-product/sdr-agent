"""
LinkedIn Signal Outreach - Pydantic Schemas
Request and Response models for API endpoints.
"""
from typing import Optional, List
from pydantic import BaseModel, Field


# ============================================
# REQUEST MODELS
# ============================================

class LinkedInSearchRequest(BaseModel):
    """Request body for LinkedIn keyword search"""
    keywords: List[str] = Field(
        ..., 
        description="List of search keywords", 
        min_length=1, 
        max_length=10
    )
    date_filter: str = Field(
        default="past-week", 
        description="One of: past-24h, past-week, past-month"
    )
    posts_per_keyword: int = Field(
        default=10, 
        ge=1, 
        le=50, 
        description="Posts to fetch per keyword"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "keywords": ["hiring software engineer", "looking for developers"],
                "date_filter": "past-week",
                "posts_per_keyword": 10
            }
        }


# ============================================
# RESPONSE MODELS
# ============================================

class LinkedInSearchResponse(BaseModel):
    """Response for search operation"""
    success: bool
    message: str
    stats: dict


class LinkedInLeadSummary(BaseModel):
    """Summary of a lead for list view (table display)"""
    id: int
    full_name: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company_name: Optional[str] = None
    is_company: bool = False
    linkedin_url: str
    headline: Optional[str] = None
    search_keyword: Optional[str] = None
    hiring_signal: bool = False
    hiring_roles: Optional[str] = None
    is_dm_sent: bool = False
    created_at: Optional[str] = None


class LinkedInLeadDetail(BaseModel):
    """Full lead details including DM (detail view)"""
    id: int
    full_name: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company_name: Optional[str] = None
    is_company: bool = False
    linkedin_url: str
    headline: Optional[str] = None
    profile_image_url: Optional[str] = None
    search_keyword: Optional[str] = None
    post_data: Optional[list] = None  # Array of posts
    hiring_signal: bool = False
    hiring_roles: Optional[str] = None
    pain_points: Optional[str] = None
    ai_variables: Optional[dict] = None
    linkedin_dm: Optional[str] = None
    is_dm_sent: bool = False
    dm_generation_status: Optional[str] = None
    dm_generation_error: Optional[str] = None
    dm_generation_started_at: Optional[str] = None
    dm_sent_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class LinkedInLeadsListResponse(BaseModel):
    """Response for leads list endpoint"""
    leads: List[LinkedInLeadSummary]
    total_count: int
    skip: int
    limit: int
    available_keywords: List[str]


class LinkedInKeywordsResponse(BaseModel):
    """Response for keywords endpoint"""
    keywords: List[str]


# ============================================
# UNIPILE DM SCHEMAS
# ============================================

class SendDMRequest(BaseModel):
    """Request to send a DM to a lead"""
    message: Optional[str] = Field(
        default=None,
        description="Custom message to send. If not provided, uses AI-generated DM."
    )

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Hi! I came across your profile and wanted to connect."
            }
        }


class SendConnectionRequest(BaseModel):
    """Request to send a connection request"""
    message: Optional[str] = Field(
        default=None,
        max_length=300,
        description="Connection note (max 300 chars). Optional."
    )


class BulkSendRequest(BaseModel):
    """Request for bulk DM or connection operations"""
    lead_ids: List[int] = Field(..., min_length=1, max_length=50)
    message: Optional[str] = Field(
        default=None,
        description="Custom message for all leads. If not provided, uses AI-generated DMs."
    )
    send_type: str = Field(
        default="dm",
        description="Type of send: 'dm' or 'connection'"
    )


class SendDMResponse(BaseModel):
    """Response for send DM operation"""
    success: bool
    message: str
    lead_id: int
    dm_status: Optional[str] = None
    sent_at: Optional[str] = None
    error: Optional[str] = None


class SendConnectionResponse(BaseModel):
    """Response for send connection operation"""
    success: bool
    message: str
    lead_id: int
    connection_status: Optional[str] = None
    invitation_id: Optional[str] = None
    sent_at: Optional[str] = None
    error: Optional[str] = None


class BulkSendResponse(BaseModel):
    """Response for bulk operations"""
    success: bool
    total: int
    successful: int
    failed: int
    results: List[dict]


class ActivityItem(BaseModel):
    """Single activity item for timeline"""
    id: int
    lead_id: int
    activity_type: str
    message: Optional[str] = None
    lead_name: Optional[str] = None
    lead_linkedin_url: Optional[str] = None
    created_at: str


class ActivitiesResponse(BaseModel):
    """Response for activities list"""
    activities: List[ActivityItem]
    total_count: int
    page: int
    limit: int
    has_more: bool


class RateLimitStatus(BaseModel):
    """Current rate limit status"""
    connections_sent_today: int 
    connections_remaining: int
    connections_limit: int
    dms_sent_today: int
    dms_remaining: int
    dms_limit: int
