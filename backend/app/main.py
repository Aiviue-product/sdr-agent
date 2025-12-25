from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1 import endpoints
# NEW IMPORT
from app.api.v1 import leads 

app = FastAPI(title=settings.PROJECT_NAME)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# file upload router
app.include_router(endpoints.router, prefix="/api/v1", tags=["File Processing"])

# Leads/Campaign Router
app.include_router(leads.router, prefix="/api/v1/leads", tags=["Leads & Campaign"])

@app.get("/")
def root():
    return {"message": "Lead Verification Pro API is running"}  