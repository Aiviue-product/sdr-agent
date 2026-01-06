from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1 import endpoints
from app.api.v1 import leads 
from app.api.v1 import enrichment  

app = FastAPI(title=settings.PROJECT_NAME)

# CORS - Using settings from Pydantic config (with fallback)
cors_origins = settings.CORS_ORIGINS if settings.CORS_ORIGINS else ["http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins, 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. File Upload Router
app.include_router(endpoints.router, prefix="/api/v1", tags=["File Processing"])

# 2. Leads/Campaign Router
app.include_router(leads.router, prefix="/api/v1/leads", tags=["Leads & Campaign"])

# 3. NEW: Enrichment Router
app.include_router(enrichment.router, prefix="/api/v1/enrichment", tags=["AI Enrichment"])

@app.get("/")
def root():
    return {"message": "Lead Verification Pro API is running"}