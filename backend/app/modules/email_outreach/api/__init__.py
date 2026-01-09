"""
Email Outreach Module - API Router
Combines all routes from this module for easy registration in main.py
"""
from fastapi import APIRouter
from app.modules.email_outreach.api import endpoints, leads, enrichment

# Create module router
router = APIRouter()

# Include sub-routers with their prefixes
router.include_router(
    endpoints.router, 
    tags=["File Processing"]
)

router.include_router(
    leads.router, 
    prefix="/leads", 
    tags=["Leads & Campaign"]
)

router.include_router(
    enrichment.router, 
    prefix="/enrichment", 
    tags=["AI Enrichment"]
)
