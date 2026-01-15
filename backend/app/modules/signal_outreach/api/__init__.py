"""
Signal Outreach Module - API Router
Combines all routes from this module for easy registration in main.py
"""
from fastapi import APIRouter
from app.modules.signal_outreach.api import endpoints

# Create module router
router = APIRouter()

# Include endpoints with prefix
router.include_router(
    endpoints.router,
    prefix="/linkedin",
    tags=["LinkedIn Signal Outreach"]
)
