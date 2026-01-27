"""
Centralized Constants for the SDR Backend Application.
All hardcoded values should be defined here for easy maintenance.
"""

# ============================================
# API TIMEOUTS (in seconds)
# ============================================
TIMEOUT_ZEROBOUNCE_INDIVIDUAL = 20.0  # Single email verification
TIMEOUT_ZEROBOUNCE_BULK = 120.0        # Batch email verification
TIMEOUT_INSTANTLY_SINGLE = 60.0       # Push single lead
TIMEOUT_INSTANTLY_BULK = 120.0         # Push bulk leads
TIMEOUT_APIFY_SCRAPER = 120.0         # LinkedIn scraper (can be slow)
TIMEOUT_GEMINI_AI = 100.0              # AI profile analysis

# ============================================
# EXTERNAL API URLS
# ============================================
# ZeroBounce Email Verification
ZEROBOUNCE_VALIDATE_URL = "https://api.zerobounce.net/v2/validate"
ZEROBOUNCE_BULK_VALIDATE_URL = "https://bulkapi.zerobounce.net/v2/validatebatch"

# Instantly.ai Email Campaign
INSTANTLY_API_URL = "https://api.instantly.ai/api/v2/leads"
INSTANTLY_BULK_API_URL = "https://api.instantly.ai/api/v2/leads/add"

# Apify LinkedIn Scraper (for profile posts - email outreach)
APIFY_LINKEDIN_ACTOR = "apimaestro/linkedin-profile-posts"

# Apify LinkedIn Posts Search (for keyword search - signal outreach)
APIFY_LINKEDIN_SEARCH_ACTOR = "apimaestro/linkedin-posts-search-scraper-no-cookies"
TIMEOUT_APIFY_LINKEDIN_SEARCH = 180.0  # Keyword search can be slower

# ============================================
# FILE PROCESSING
# ============================================
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
FILE_CHUNK_SIZE_BYTES = 1024 * 1024     # 1 MB chunks for streaming
ALLOWED_EXTENSIONS = {".xlsx", ".csv"}
ALLOWED_MIME_TYPES = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/csv",
    "application/csv"
}
 
# ============================================
# BATCH PROCESSING LIMITS
# ============================================
MAX_BULK_LEADS = 100          # Max leads per bulk push
MAX_BULK_EMAILS = 100         # Max emails per ZeroBounce batch
MAX_SCRAPER_POSTS = 2         # Default posts to scrape per profile

# ============================================
# AI MODEL CONFIGURATION
# ============================================
GEMINI_MODEL_NAME = "gemini-2.5-flash"

# ============================================
# LINKEDIN / UNIPILE RATE LIMITS
# ============================================
LINKEDIN_DAILY_CONNECTION_LIMIT = 25      # Max connection requests per day
LINKEDIN_DAILY_DM_LIMIT = 150             # Max DMs per day
LINKEDIN_BULK_DELAY_SECONDS = 5           # Delay between bulk sends

# Unipile API Timeouts
TIMEOUT_UNIPILE_API = 30.0                # General Unipile API timeout
TIMEOUT_UNIPILE_PROFILE = 15.0            # Get profile timeout
TIMEOUT_UNIPILE_MESSAGE = 20.0            # Send message timeout

# ============================================
# DATABASE POOL SETTINGS
# ============================================
DB_POOL_SIZE = 5
DB_MAX_OVERFLOW = 10
DB_POOL_RECYCLE = 300
