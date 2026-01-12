# backend/tests/database/test_db_connection.py
"""
Database Connection & Health Tests

SIMPLIFIED VERSION: Uses inline connections to avoid pytest-asyncio event loop issues.
"""

import pytest
import asyncio
import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load env
load_dotenv()


def get_database_url():
    """Get database URL from environment."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL not set")
    return url


# --- SIMPLE ASYNC HELPER ---
async def run_query(query_string: str):
    """Run a single query and return result."""
    engine = create_async_engine(
        get_database_url(), 
        echo=False,
        connect_args={"statement_cache_size": 0, "prepared_statement_cache_size": 0}
    )
    async_session = sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        result = await session.execute(text(query_string))
        data = result.fetchall()
        await session.close()
    
    await engine.dispose()
    return data


async def run_scalar(query_string: str):
    """Run a query and return scalar result."""
    engine = create_async_engine(
        get_database_url(), 
        echo=False,
        connect_args={"statement_cache_size": 0, "prepared_statement_cache_size": 0}
    )
    async_session = sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        result = await session.execute(text(query_string))
        scalar = result.scalar()
        await session.close()
    
    await engine.dispose()
    return scalar


# --- TESTS ---
def test_database_connection_works():
    """
    Verify that we can establish a connection to the database.
    """
    result = asyncio.run(run_scalar("SELECT 1"))
    assert result == 1, "Database should return 1 for SELECT 1"


def test_database_connection_returns_version():
    """
    Verify database is PostgreSQL.
    """
    result = asyncio.run(run_scalar("SELECT version()"))
    assert "PostgreSQL" in result, "Should be connected to PostgreSQL"


def test_leads_table_exists():
    """
    Verify that the 'leads' table exists.
    """
    result = asyncio.run(run_scalar("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'leads'
        );
    """))
    assert result is True, "Table 'leads' must exist"


def test_leads_table_has_required_columns():
    """
    Verify that the leads table has all required columns.
    """
    required_columns = [
        # Primary Key
        'id',
        # Contact Info
        'email', 'first_name', 'last_name', 'company_name',
        'linkedin_url', 'mobile_number',
        # Classification
        'designation', 'sector', 'priority',
        # Verification Results
        'verification_status', 'verification_tag', 'lead_stage',
        # FATE Generated Emails (Body)
        'email_1_body', 'email_2_body', 'email_3_body',
        # FATE Generated Emails (Subject)
        'email_1_subject', 'email_2_subject', 'email_3_subject',
        # AI Enrichment Fields
        'enrichment_status', 'hiring_signal', 'ai_variables', 
        'personalized_intro', 'scraped_data',
        # Campaign Metadata
        'is_sent', 'sent_at', 'instantly_lead_id',
        # Timestamps
        'created_at', 'updated_at'
    ]
    
    rows = asyncio.run(run_query("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'leads';
    """))
    existing_columns = [row[0] for row in rows]
    
    missing_columns = [col for col in required_columns if col not in existing_columns]
    
    assert len(missing_columns) == 0, f"Missing columns: {missing_columns}"


def test_fate_matrix_table_exists():
    """
    Verify that the 'fate_matrix' table exists.
    """
    result = asyncio.run(run_scalar("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'fate_matrix'
        );
    """))
    assert result is True, "Table 'fate_matrix' must exist"


def test_fate_matrix_has_data():
    """
    Verify fate_matrix has at least 1 rule.
    """
    result = asyncio.run(run_scalar("SELECT COUNT(*) FROM fate_matrix"))
    assert result > 0, "FATE matrix must have at least 1 rule"


def test_database_timezone():
    """
    Verify database returns timestamps.
    """
    result = asyncio.run(run_scalar("SELECT NOW()"))
    assert result is not None, "Database should return current timestamp"


def test_list_available_sectors():
    """
    Utility test to show available sectors in FATE matrix.
    """
    rows = asyncio.run(run_query("""
        SELECT DISTINCT sector FROM fate_matrix ORDER BY sector
    """))
    sectors = [row[0] for row in rows]
    
    print(f"\n📋 Available sectors in FATE matrix: {sectors}")
    assert len(sectors) >= 0  # Just for visibility, not a hard requirement
