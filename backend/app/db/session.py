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

# Add query parameter to disable prepared statements for PgBouncer/Transaction Pooler
# This is the correct way for SQLAlchemy + asyncpg
if "?" in DATABASE_URL:
    DATABASE_URL += "&prepared_statement_cache_size=0"
else:
    DATABASE_URL += "?prepared_statement_cache_size=0"

# Create Async Engine (no connect_args needed - handled via URL)
engine = create_async_engine(
    DATABASE_URL, 
    echo=False, 
    pool_pre_ping=True
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