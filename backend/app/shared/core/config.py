from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Lead Verification Pro" 
    API_V1_STR: str = "/api/v1"
    APIFY_TOKEN: str
    ZEROBOUNCE_API_KEY: str
    GEMINI_API_KEY: str
    CORS_ORIGIN: str = "http://localhost:3000"  
    DATABASE_URL: str 
    
    # Unipile LinkedIn Messaging API
    UNIPILE_API_KEY: str = ""
    UNIPILE_DSN: str = "https://api16.unipile.com:14612"
    UNIPILE_ACCOUNT_ID: str = ""
    UNIPILE_WEBHOOK_SECRET: str = ""  # Optional: Set to enable webhook signature verification

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore" 
    )

settings = Settings()     
