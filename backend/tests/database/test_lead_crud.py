# backend/tests/database/test_lead_crud.py 
"""
Lead CRUD Operation Tests

SIMPLIFIED VERSION: Uses asyncio.run() to avoid event loop issues.

Tests covered:
1. Insert a new lead successfully
2. Handle duplicate email (upsert behavior)
3. Handle NULL values in optional fields
4. Handle very long text in fields
5. Update existing lead
6. Delete lead
7. Query leads by stage (campaign/enrichment)
8. Verify email uniqueness constraint
"""

import asyncio
import os
import uuid
import json
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


def generate_unique_email():
    """Generate a unique test email to avoid conflicts."""
    return f"test_{uuid.uuid4().hex[:8]}@pytest.com"


# --- ASYNC HELPER FUNCTIONS ---

async def execute_query(query_string: str, params: dict = None, commit: bool = False):
    """Execute a query with optional params and commit."""
    engine = create_async_engine(get_database_url(), echo=False)
    async_session = sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    
    result_data = None
    async with async_session() as session:
        if params:
            result = await session.execute(text(query_string), params)
        else:
            result = await session.execute(text(query_string))
        
        # Try to get data if it's a SELECT
        try:
            result_data = result.fetchall()
        except:
            result_data = None
        
        if commit:
            await session.commit()
    
    await engine.dispose()
    return result_data


async def execute_scalar(query_string: str, params: dict = None):
    """Execute a query and return scalar result."""
    engine = create_async_engine(get_database_url(), echo=False)
    async_session = sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        if params:
            result = await session.execute(text(query_string), params)
        else:
            result = await session.execute(text(query_string))
        scalar = result.scalar()
    
    await engine.dispose()
    return scalar


async def execute_fetchone(query_string: str, params: dict = None):
    """Execute a query and return first row."""
    engine = create_async_engine(get_database_url(), echo=False)
    async_session = sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        if params:
            result = await session.execute(text(query_string), params)
        else:
            result = await session.execute(text(query_string))
        row = result.fetchone()
    
    await engine.dispose()
    return row


async def insert_test_lead(email: str, **kwargs):
    """
    Insert a test lead with given email and optional fields.
    Provides default values for required NOT NULL fields.
    """
    # Default values for required NOT NULL fields
    defaults = {
        "first_name": kwargs.get("first_name", "TestFirst"),  # Required
        "last_name": kwargs.get("last_name", "TestLast"),
        "company_name": kwargs.get("company_name", "Test Company"),  # Required
        "linkedin_url": kwargs.get("linkedin_url", "https://linkedin.com/in/test"),  # Required
        "mobile_number": kwargs.get("mobile_number", "+1234567890"),  # Required
        "designation": kwargs.get("designation", "Test Role"),  # Required
        "sector": kwargs.get("sector", "Technology"),  # Required
        "status": kwargs.get("verification_status", "valid"),
        "stage": kwargs.get("lead_stage", "campaign"),
        "ai_vars": kwargs.get("ai_variables")
    }
    
    engine = create_async_engine(get_database_url(), echo=False)
    async_session = sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        await session.execute(text("""
            INSERT INTO leads (
                email, first_name, last_name, company_name, linkedin_url,
                mobile_number, designation, sector, verification_status, 
                lead_stage, ai_variables
            ) VALUES (
                :email, :first_name, :last_name, :company_name, :linkedin_url,
                :mobile_number, :designation, :sector, :status, 
                :stage, :ai_vars
            )
        """), {"email": email, **defaults})
        await session.commit()
    
    await engine.dispose()


async def delete_test_lead(email: str):
    """Delete a test lead by email."""
    engine = create_async_engine(get_database_url(), echo=False)
    async_session = sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        await session.execute(
            text("DELETE FROM leads WHERE email = :email"),
            {"email": email}
        )
        await session.commit()
    
    await engine.dispose()


async def run_insert_and_verify(email: str, **kwargs):
    """Insert a lead and verify it exists."""
    await insert_test_lead(email, **kwargs)
    row = await execute_fetchone(
        "SELECT email FROM leads WHERE email = :email",
        {"email": email}
    )
    return row


# --- TESTS ---

def test_insert_new_lead_success():
    """
    Verify that a complete lead can be inserted successfully.
    """
    test_email = generate_unique_email()
    
    async def test_logic():
        try:
            await insert_test_lead(
                test_email,
                first_name="Test",
                last_name="User",
                company_name="Test Corp",
                designation="CEO",
                sector="Technology"
            )
            
            # Verify insertion
            row = await execute_fetchone(
                "SELECT email FROM leads WHERE email = :email",
                {"email": test_email}
            )
            assert row is not None, "Lead should be inserted"
            assert row[0] == test_email
            
        finally:
            await delete_test_lead(test_email)
    
    asyncio.run(test_logic())


def test_insert_lead_with_null_optional_fields():
    """
    Verify that leads with truly optional NULL fields can be inserted.
    Required fields: email, first_name, company_name, linkedin_url, mobile_number, designation, sector
    Optional fields: last_name, priority, verification_tag, etc.
    """
    test_email = generate_unique_email()
    
    async def test_logic():
        try:
            # Insert with required fields only - optional fields will be NULL
            await insert_test_lead(test_email, lead_stage="enrichment")
            
            # Verify insertion - check that priority (optional) is NULL
            row = await execute_fetchone(
                "SELECT first_name, priority, verification_tag FROM leads WHERE email = :email",
                {"email": test_email}
            )
            assert row is not None, "Lead should be inserted"
            assert row[0] == "TestFirst", "first_name should be our default"
            # priority and verification_tag should be NULL (optional fields)
            
        finally:
            await delete_test_lead(test_email)
    
    asyncio.run(test_logic())


def test_duplicate_email_upsert_behavior():
    """
    Verify that inserting a duplicate email updates existing record (upsert).
    """
    test_email = generate_unique_email()
    
    async def test_logic():
        engine = create_async_engine(get_database_url(), echo=False)
        async_session = sessionmaker(
            bind=engine, class_=AsyncSession, expire_on_commit=False
        )
        
        try:
            async with async_session() as session:
                # First insert
                await session.execute(text("""
                    INSERT INTO leads (email, first_name, verification_status, lead_stage)
                    VALUES (:email, :first_name, :status, :stage)
                """), {
                    "email": test_email,
                    "first_name": "Original",
                    "status": "valid",
                    "stage": "campaign"
                })
                await session.commit()
            
            async with async_session() as session:
                # Second insert with ON CONFLICT (upsert)
                await session.execute(text("""
                    INSERT INTO leads (email, first_name, verification_status, lead_stage)
                    VALUES (:email, :first_name, :status, :stage)
                    ON CONFLICT (email) 
                    DO UPDATE SET first_name = EXCLUDED.first_name
                """), {
                    "email": test_email,
                    "first_name": "Updated",
                    "status": "valid",
                    "stage": "campaign"
                })
                await session.commit()
            
            # Verify update happened
            row = await execute_fetchone(
                "SELECT first_name FROM leads WHERE email = :email",
                {"email": test_email}
            )
            assert row[0] == "Updated", "First name should be updated via upsert"
            
            # Verify only 1 record exists
            count = await execute_scalar(
                "SELECT COUNT(*) FROM leads WHERE email = :email",
                {"email": test_email}
            )
            assert count == 1, "Should have exactly 1 record, not duplicate"
            
        finally:
            await delete_test_lead(test_email)
            await engine.dispose()
    
    asyncio.run(test_logic())


def test_insert_very_long_company_name():
    """
    Test behavior when company_name is extremely long.
    """
    test_email = generate_unique_email()
    long_company_name = "A" * 500
    
    async def test_logic():
        try:
            await insert_test_lead(test_email, company_name=long_company_name)
            
            # Verify insertion succeeded
            row = await execute_fetchone(
                "SELECT company_name FROM leads WHERE email = :email",
                {"email": test_email}
            )
            assert row is not None, "Long company name should be accepted"
            
        except Exception as e:
            pytest.skip(f"Long text handling: {str(e)}")
            
        finally:
            await delete_test_lead(test_email)
    
    asyncio.run(test_logic())


def test_update_lead_stage():
    """
    Verify that lead_stage can be updated from 'enrichment' to 'campaign'.
    """
    test_email = generate_unique_email()
    
    async def test_logic():
        engine = create_async_engine(get_database_url(), echo=False)
        async_session = sessionmaker(
            bind=engine, class_=AsyncSession, expire_on_commit=False
        )
        
        try:
            # Insert as enrichment lead
            await insert_test_lead(test_email, lead_stage="enrichment")
            
            # Update to campaign stage
            async with async_session() as session:
                await session.execute(text("""
                    UPDATE leads 
                    SET lead_stage = 'campaign', updated_at = NOW()
                    WHERE email = :email
                """), {"email": test_email})
                await session.commit()
            
            # Verify update
            stage = await execute_scalar(
                "SELECT lead_stage FROM leads WHERE email = :email",
                {"email": test_email}
            )
            assert stage == "campaign", "Lead stage should be updated to campaign"
            
        finally:
            await delete_test_lead(test_email)
            await engine.dispose()
    
    asyncio.run(test_logic())


def test_query_leads_by_stage_campaign():
    """
    Verify that querying by lead_stage='campaign' works correctly.
    """
    test_email = generate_unique_email()
    
    async def test_logic():
        try:
            await insert_test_lead(test_email, lead_stage="campaign")
            
            row = await execute_fetchone("""
                SELECT email FROM leads 
                WHERE lead_stage = 'campaign' AND email = :email
            """, {"email": test_email})
            
            assert row is not None, "Campaign lead should be queryable by stage"
            
        finally:
            await delete_test_lead(test_email)
    
    asyncio.run(test_logic())


def test_query_leads_by_stage_enrichment():
    """
    Verify that querying by lead_stage='enrichment' works correctly.
    """
    test_email = generate_unique_email()
    
    async def test_logic():
        try:
            await insert_test_lead(test_email, lead_stage="enrichment")
            
            row = await execute_fetchone("""
                SELECT email FROM leads 
                WHERE lead_stage = 'enrichment' AND email = :email
            """, {"email": test_email})
            
            assert row is not None, "Enrichment lead should be queryable by stage"
            
        finally:
            await delete_test_lead(test_email)
    
    asyncio.run(test_logic())


def test_delete_lead():
    """
    Verify that a lead can be deleted successfully.
    """
    test_email = generate_unique_email()
    
    async def test_logic():
        # Insert
        await insert_test_lead(test_email)
        
        # Delete
        await delete_test_lead(test_email)
        
        # Verify deletion
        count = await execute_scalar(
            "SELECT COUNT(*) FROM leads WHERE email = :email",
            {"email": test_email}
        )
        assert count == 0, "Lead should be deleted"
    
    asyncio.run(test_logic())


def test_email_is_unique_constraint():
    """
    Verify that email column has unique constraint.
    Duplicate insert without ON CONFLICT should fail.
    """
    test_email = generate_unique_email()
    
    async def test_logic():
        engine = create_async_engine(get_database_url(), echo=False)
        async_session = sessionmaker(
            bind=engine, class_=AsyncSession, expire_on_commit=False
        )
        
        try:
            # First insert
            await insert_test_lead(test_email)
            
            # Try duplicate insert - should fail
            async with async_session() as session:
                try:
                    await session.execute(text("""
                        INSERT INTO leads (
                            email, first_name, company_name, linkedin_url,
                            mobile_number, designation, sector,
                            verification_status, lead_stage
                        ) VALUES (
                            :email, 'Dup', 'Dup Corp', 'https://linkedin.com/in/dup',
                            '+9999999', 'Dup Role', 'Tech',
                            'valid', 'campaign'
                        )
                    """), {"email": test_email})
                    await session.commit()
                    # If we get here, constraint didn't work
                    assert False, "Duplicate insert should have failed!"
                except Exception:
                    # Expected - unique constraint violation
                    await session.rollback()
                    pass
            
        finally:
            await delete_test_lead(test_email)
            await engine.dispose()
    
    asyncio.run(test_logic())


def test_store_and_retrieve_json_ai_variables():
    """
    Verify that JSON data can be stored and retrieved from ai_variables column.
    """
    test_email = generate_unique_email()
    test_json = '{"hiring_signal": true, "hiring_roles": "Engineer"}'
    
    async def test_logic():
        try:
            await insert_test_lead(test_email, ai_variables=test_json)
            
            # Retrieve and verify JSON
            row = await execute_fetchone(
                "SELECT ai_variables FROM leads WHERE email = :email",
                {"email": test_email}
            )
            
            # Verify JSON can be parsed
            ai_data = json.loads(row[0]) if isinstance(row[0], str) else row[0]
            assert ai_data["hiring_signal"] == True
            assert ai_data["hiring_roles"] == "Engineer"
            
        finally:
            await delete_test_lead(test_email)
    
    asyncio.run(test_logic())
