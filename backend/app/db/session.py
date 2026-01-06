import os
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession 
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL") 

if not DATABASE_URL:
    logger.error("❌ DATABASE_URL is missing in .env file")
    raise ValueError("DATABASE_URL is required")

# Create Async Engine
engine = create_async_engine(
    DATABASE_URL, 
    echo=False, 
    pool_pre_ping=True,
    # ⚠️ CRITICAL FIX BELOW:
    # Use "prepare_threshold": None for asyncpg with Supabase Transaction Pooler.
    # "statement_cache_size": 0 is for psycopg2 and won't work here.
    connect_args={"prepare_threshold": None} 
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