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
    UNIPILE_DSN: str = "https://api12.unipile.com:14263" 
    UNIPILE_ACCOUNT_ID: str = ""
    UNIPILE_WEBHOOK_SECRET: str = ""  # Optional: Set to enable webhook signature verification

    # WATI WhatsApp Messaging API
    WATI_API_TOKEN: str = ""
    WATI_API_ENDPOINT: str = "https://live-mt-server.wati.io/105961"
    WATI_CHANNEL_NUMBER: str = ""  # Your WhatsApp Business number (sender)
    WATI_DEFAULT_COUNTRY_CODE: str = "91"  # Default country code (India)
    WATI_WEBHOOK_SECRET: str = ""  # Secret token for webhook verification (set in .env)
    WATI_WEBHOOK_ALLOWED_IPS: str = ""  # Comma-separated IPs to whitelist (optional)

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore" 
    )

settings = Settings()      
