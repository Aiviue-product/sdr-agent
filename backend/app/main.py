from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.shared.core.config import settings
from app.shared.core.logging import setup_logging
from app.shared.middleware.correlation import CorrelationIdMiddleware
from app.shared.utils.http_client import startup_http_client, shutdown_http_client
from app.modules.signal_outreach.api import router as signal_outreach_router
from app.modules.email_outreach.api import router as email_outreach_router
from app.modules.whatsapp_outreach.api import router as whatsapp_outreach_router

# Setup logging with correlation ID support
setup_logging()


# ============================================
# LIFESPAN - STARTUP/SHUTDOWN HOOKS
# ============================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    
    Startup: Initialize HTTP client pool, pre-warm connections
    Shutdown: Properly close all HTTP connections
    """
    # STARTUP
    await startup_http_client()
    
    yield  # Application runs here
    
    # SHUTDOWN
    await shutdown_http_client()


app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

# ============================================
# MIDDLEWARE (order matters - first added = outermost)
# ============================================

# Correlation ID Middleware - Assigns unique request ID for log tracing
app.add_middleware(CorrelationIdMiddleware)

# CORS - Using single origin from settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.CORS_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],  # Allow frontend to see request ID
)


# ============================================
# MODULE ROUTERS
# ============================================

# Email Outreach Module (Leads, Campaign, Enrichment, File Upload)
app.include_router(email_outreach_router, prefix="/api/v1")

# Signal Outreach Module (LinkedIn keyword search, AI analysis, DM generation)
app.include_router(signal_outreach_router, prefix="/api/v1")

# WhatsApp Outreach Module (WATI integration, template messages, webhooks)
app.include_router(whatsapp_outreach_router, prefix="/api/v1/whatsapp", tags=["WhatsApp"]) 


@app.get("/")
def root():
    return {"message": "Lead Verification Pro API is running"}

