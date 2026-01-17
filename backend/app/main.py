from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.shared.core.config import settings
from app.modules.signal_outreach.api import router as signal_outreach_router
from app.modules.email_outreach.api import router as email_outreach_router

app = FastAPI(title=settings.PROJECT_NAME)

# CORS - Using single origin from settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.CORS_ORIGIN],   # Wrap single string in list
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"], 
)


# ============================================
# MODULE ROUTERS
# ============================================

# Email Outreach Module (Leads, Campaign, Enrichment, File Upload)
app.include_router(email_outreach_router, prefix="/api/v1")

# Signal Outreach Module (LinkedIn keyword search, AI analysis, DM generation)
app.include_router(signal_outreach_router, prefix="/api/v1") 


@app.get("/")
def root():
    return {"message": "Lead Verification Pro API is running"}
