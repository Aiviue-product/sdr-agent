"""
Signal Outreach Module - API Router
Combines all routes from this module for easy registration in main.py
"""
from fastapi import APIRouter
from app.modules.signal_outreach.api import endpoints
from app.modules.signal_outreach.api import unipile_endpoints

# Create module router
router = APIRouter()

# Include existing LinkedIn endpoints
router.include_router(
    endpoints.router,
    prefix="/linkedin",
    tags=["LinkedIn Signal Outreach"] 
)

# Include Unipile DM endpoints
router.include_router(
    unipile_endpoints.router,
    prefix="/linkedin/dm",
    tags=["LinkedIn DM Outreach"]
)
