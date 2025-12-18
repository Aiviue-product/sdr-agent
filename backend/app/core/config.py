from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    PROJECT_NAME: str = "Lead Verification Pro" 
    API_V1_STR: str = "/api/v1"
    ZEROBOUNCE_API_KEY: str
    CORS_ORIGINS: List[str] = [] 
    DATABASE_URL: str 

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore" 
    )

settings = Settings() 