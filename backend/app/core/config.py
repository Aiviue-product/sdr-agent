from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    PROJECT_NAME: str = "Lead Verification API"    
    API_V1_STR: str = "/api/v1"
    ZEROBOUNCE_API_KEY: str
    CORS_ORIGINS: List[str] = []

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()