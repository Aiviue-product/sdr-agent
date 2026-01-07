import os
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession 
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from app.core.constants import DB_POOL_SIZE, DB_MAX_OVERFLOW, DB_POOL_RECYCLE

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL") 

if not DATABASE_URL:
    logger.error("❌ DATABASE_URL is missing in .env file")
    raise ValueError("DATABASE_URL is required")

# Create Async Engine with PgBouncer/Transaction Pooler compatibility
# statement_cache_size=0 disables prepared statements (required for PgBouncer)
engine = create_async_engine(
    DATABASE_URL, 
    echo=False, 
    pool_pre_ping=True,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    pool_recycle=DB_POOL_RECYCLE,
    connect_args={
        "statement_cache_size": 0,      # Disable prepared statement cache
        "prepared_statement_cache_size": 0  # Also disable this for safety
    }
)

# Session Factory
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

# Updated log message to match reality
logger.info("✅ Database Engine Initialized (Transaction Pooler)")

async def get_db():
    """Dependency for FastAPI routes to get a DB session"""
    async with AsyncSessionLocal() as session:
        yield session  