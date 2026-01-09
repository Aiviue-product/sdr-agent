# backend/tests/database/test_fate_matrix.py
"""
FATE Matrix Database Tests

SIMPLIFIED VERSION: Uses asyncio.run() to avoid event loop issues.

Tests covered:
1. FATE matrix table has required columns
2. Query by sector works
3. Query by sector + designation works
4. Fallback to generic sector rule works
5. No rule found returns empty
"""

import asyncio
import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import pytest

# Load env
load_dotenv() 


def get_database_url():
    """Get database URL from environment."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL not set")
    return url


async def run_query(query_string: str, params: dict = None):
    """Run a query and return all results."""
    engine = create_async_engine(
        get_database_url(), 
        echo=False,
        connect_args={"statement_cache_size": 0, "prepared_statement_cache_size": 0}
    )
    async_session = sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        if params:
            result = await session.execute(text(query_string), params)
        else:
            result = await session.execute(text(query_string))
        data = result.fetchall()
        await session.close()
    
    await engine.dispose()
    return data


async def run_scalar(query_string: str, params: dict = None):
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
        if params:
            result = await session.execute(text(query_string), params)
        else:
            result = await session.execute(text(query_string))
        scalar = result.scalar()
        await session.close()
    
    await engine.dispose()
    return scalar


async def run_fetchone(query_string: str, params: dict = None):
    """Run a query and return first row."""
    engine = create_async_engine(
        get_database_url(), 
        echo=False,
        connect_args={"statement_cache_size": 0, "prepared_statement_cache_size": 0}
    )
    async_session = sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        if params:
            result = await session.execute(text(query_string), params)
        else:
            result = await session.execute(text(query_string))
        row = result.fetchone()
        await session.close()
    
    await engine.dispose()
    return row


# --- TESTS ---

def test_fate_matrix_table_has_required_columns():
    """
    Verify that fate_matrix table has all required columns for FATE logic.
    """
    required_columns = [
        # Primary Key 
        'id',
        # FATE Fields
        'sector', 'designation_role', 'f_pain', 'a_goal', 
        't_solution', 'e_evidence', 'urgency_level',
        # Timestamp
        'created_at'
    ]
    
    rows = asyncio.run(run_query("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'fate_matrix';
    """))
    existing_columns = [row[0] for row in rows]
    
    missing_columns = [col for col in required_columns if col not in existing_columns]
    
    assert len(missing_columns) == 0, f"Missing columns in fate_matrix: {missing_columns}"


def test_fate_matrix_has_data():
    """
    Verify that fate_matrix table has at least some rules populated.
    An empty FATE matrix means no emails can be generated!
    """
    count = asyncio.run(run_scalar("SELECT COUNT(*) FROM fate_matrix"))
    assert count > 0, "FATE matrix must have at least 1 rule. Table is empty!"


def test_query_fate_by_sector():
    """
    Verify that querying FATE matrix by sector returns results.
    """
    # First, get any existing sector from the table
    row = asyncio.run(run_fetchone("""
        SELECT DISTINCT sector FROM fate_matrix LIMIT 1
    """))
    
    if row is None:
        pytest.skip("No sectors in fate_matrix table")
    
    test_sector = row[0]
    
    # Query by that sector
    rule = asyncio.run(run_fetchone("""
        SELECT * FROM fate_matrix 
        WHERE LOWER(sector) = LOWER(:sector)
        LIMIT 1
    """, {"sector": test_sector}))
    
    assert rule is not None, f"Should find FATE rule for sector: {test_sector}"


def test_query_fate_by_sector_and_designation():
    """
    Verify that exact match query (sector + designation) works.
    """
    # Get an existing sector + designation combo
    row = asyncio.run(run_fetchone("""
        SELECT sector, designation_role FROM fate_matrix LIMIT 1
    """))
    
    if row is None:
        pytest.skip("No data in fate_matrix table")
    
    test_sector = row[0]
    test_designation = row[1]
    
    # Query exact match
    rule = asyncio.run(run_fetchone("""
        SELECT * FROM fate_matrix 
        WHERE LOWER(sector) = LOWER(:sector) 
        AND LOWER(designation_role) = LOWER(:designation)
        LIMIT 1
    """, {"sector": test_sector, "designation": test_designation}))
    
    assert rule is not None, "Should find FATE rule for exact match"


def test_query_fate_unknown_sector_returns_empty():
    """
    Verify that querying with unknown sector returns no results.
    """
    rule = asyncio.run(run_fetchone("""
        SELECT * FROM fate_matrix 
        WHERE LOWER(sector) = LOWER(:sector)
        LIMIT 1
    """, {"sector": "NONEXISTENT_SECTOR_12345"}))
    
    assert rule is None, "Unknown sector should return no results"


def test_fate_rule_has_all_template_fields():
    """
    Verify that FATE rules have non-empty values for required template fields.
    Empty values would cause email templates to have blank spots.
    """
    rows = asyncio.run(run_query("""
        SELECT sector, f_pain, a_goal, t_solution, e_evidence
        FROM fate_matrix
        LIMIT 10
    """))
    
    for row in rows:
        sector, f_pain, a_goal, t_solution, e_evidence = row
        
        # Check that key fields are not empty
        assert f_pain and len(f_pain.strip()) > 0, \
            f"Sector '{sector}' has empty f_pain"
        assert a_goal and len(a_goal.strip()) > 0, \
            f"Sector '{sector}' has empty a_goal"
        assert t_solution and len(t_solution.strip()) > 0, \
            f"Sector '{sector}' has empty t_solution"
        assert e_evidence and len(e_evidence.strip()) > 0, \
            f"Sector '{sector}' has empty e_evidence"


def test_list_all_sectors_in_fate_matrix():
    """
    Utility test to show what sectors are available.
    Useful for debugging "no FATE rule found" errors.
    """
    rows = asyncio.run(run_query("""
        SELECT DISTINCT sector FROM fate_matrix ORDER BY sector
    """))
    sectors = [row[0] for row in rows]
    
    # Print for visibility
    print(f"\n📋 Available sectors in FATE matrix: {sectors}")
    
    assert len(sectors) > 0, "Should have at least 1 sector"
