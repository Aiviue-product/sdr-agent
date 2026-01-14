"""
Email Outreach Models Package

This module exports:
- ORM Models (SQLAlchemy): For database schema definition (used by Alembic)
- Pydantic Schemas: For API request/response validation
"""

# ============================================
# ORM MODELS (SQLAlchemy - Database Schema)
# ============================================
from app.modules.email_outreach.models.lead import Lead
from app.modules.email_outreach.models.fate_matrix import FateMatrix

# ============================================
# PYDANTIC SCHEMAS (API Validation)
# ============================================
from app.modules.email_outreach.models.email import (
    SendEmailRequest,
    SendSequenceRequest,
)

# Export all for easy imports
__all__ = [
    # ORM Models
    "Lead",
    "FateMatrix",
    # Pydantic Schemas
    "SendEmailRequest",
    "SendSequenceRequest",
]
