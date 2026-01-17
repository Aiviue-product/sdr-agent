"""
Alembic Environment Configuration

This file configures how Alembic runs migrations.
It's set up to:
1. Read DATABASE_URL from environment variables
2. Import all ORM models for autogenerate support
3. Work with your existing Supabase PostgreSQL database
"""
import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the backend directory to Python path so we can import our models
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ============================================
# IMPORT YOUR MODELS HERE
# This is required for autogenerate to detect schema changes
# ============================================
from app.shared.db.base import Base
from app.modules.email_outreach.models.lead import Lead
from app.modules.email_outreach.models.fate_matrix import FateMatrix
from app.modules.signal_outreach.models.linkedin_lead import LinkedInLead

# This is the Alembic Config object
config = context.config

# Set the database URL from environment variable
# This overrides whatever is in alembic.ini
DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL:
    # Alembic needs a SYNC driver, not async
    # Convert asyncpg URL to psycopg2 URL for migrations
    SYNC_DATABASE_URL = DATABASE_URL.replace(
        "postgresql+asyncpg://", 
        "postgresql+psycopg2://"
    ).replace(
        "postgresql://",
        "postgresql+psycopg2://"
    )
    config.set_main_option("sqlalchemy.url", SYNC_DATABASE_URL)
else:
    raise ValueError("DATABASE_URL environment variable is not set!")

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ============================================
# TARGET METADATA
# This tells Alembic what your schema "should" look like
# ============================================
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.
    
    This generates SQL scripts without connecting to the database.
    Useful for reviewing what SQL will be executed.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.
    
    This connects to your database and executes migrations directly.
    This is the mode you'll use most often.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata,
            # Compare types (e.g., String(50) vs String(100))
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
