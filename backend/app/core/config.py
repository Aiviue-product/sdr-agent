from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import List, Union
import json

class Settings(BaseSettings):
    PROJECT_NAME: str = "Lead Verification Pro" 
    API_V1_STR: str = "/api/v1"
    APIFY_TOKEN: str
    ZEROBOUNCE_API_KEY: str
    GEMINI_API_KEY: str
    CORS_ORIGINS: List[str] = []  
    DATABASE_URL: str 

    @field_validator('CORS_ORIGINS', mode='before')
    @classmethod
    def parse_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        """Parse CORS_ORIGINS from JSON string or comma-separated values."""
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            # Try to parse as JSON first
            if v.startswith('['):
                try:
                    return json.loads(v)
                except json.JSONDecodeError:
                    pass
            # Fall back to comma-separated values
            return [origin.strip() for origin in v.split(',') if origin.strip()]
        return []

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore" 
    )

settings = Settings() 