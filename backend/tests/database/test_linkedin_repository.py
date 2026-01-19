import asyncio
import os
import uuid
import json
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import pytest

from app.modules.signal_outreach.repositories.linkedin_lead_repository import LinkedInLeadRepository
from app.modules.signal_outreach.models.linkedin_lead import LinkedInLead

# Load env
load_dotenv()

def get_database_url():
    """Get database URL from environment."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL not set")
    return url

def generate_unique_url():
    """Generate a unique test LinkedIn URL to avoid conflicts."""
    return f"https://linkedin.com/in/test_{uuid.uuid4().hex[:8]}"

# --- ASYNC HELPER FOR TESTS ---
async def get_test_repo_and_session():
    """Create a temporary session and repository for testing."""
    engine = create_async_engine(
        get_database_url(), 
        echo=False,
        connect_args={"statement_cache_size": 0, "prepared_statement_cache_size": 0}
    )
    async_session = sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    session = async_session()
    repo = LinkedInLeadRepository(session)
    return engine, session, repo

async def cleanup(engine, session, lead_id=None):
    """Cleanup test data and close connections."""
    if lead_id:
        await session.execute(text("DELETE FROM linkedin_outreach_leads WHERE id = :id"), {"id": lead_id})
        await session.commit()
    await session.close()
    await engine.dispose()

# --- TESTS ---

def test_repo_insert_and_get_by_id():
    """
    Verify that a LinkedIn lead can be inserted and retrieved via ORI methods.
    """
    test_url = generate_unique_url()
    
    async def test_logic():
        engine, session, repo = await get_test_repo_and_session()
        lead_id = None
        try:
            # Insert a lead manually first to test the ORM read
            new_lead = LinkedInLead(
                full_name="Test User",
                linkedin_url=test_url,
                search_keyword="hiring"
            )
            session.add(new_lead)
            await session.commit()
            lead_id = new_lead.id
            
            # 1. Test get_by_id (Refactored to ORM)
            retrieved = await repo.get_by_id(lead_id)
            assert retrieved is not None
            assert retrieved["full_name"] == "Test User"
            assert retrieved["linkedin_url"] == test_url
            
        finally:
            await cleanup(engine, session, lead_id)
    
    asyncio.run(test_logic())

def test_repo_get_leads_by_ids():
    """
    Verify bulk retrieval of leads by IDs.
    """
    url1 = generate_unique_url()
    url2 = generate_unique_url()
    
    async def test_logic():
        engine, session, repo = await get_test_repo_and_session()
        ids = []
        try:
            l1 = LinkedInLead(full_name="User 1", linkedin_url=url1)
            l2 = LinkedInLead(full_name="User 2", linkedin_url=url2)
            session.add_all([l1, l2])
            await session.commit()
            ids = [l1.id, l2.id]
            
            # Test bulk fetch (Refactored to ORM)
            leads = await repo.get_leads_by_ids(ids)
            assert len(leads) == 2
            assert any(l["full_name"] == "User 1" for l in leads)
            assert any(l["full_name"] == "User 2" for l in leads)
            
        finally:
            for lid in ids:
                await session.execute(text("DELETE FROM linkedin_outreach_leads WHERE id = :id"), {"id": lid})
            await session.commit()
            await cleanup(engine, session)
            
    asyncio.run(test_logic())

def test_repo_update_operations():
    """
    Verify ORM update methods (DM sent, Enrichment).
    """
    test_url = generate_unique_url()
    
    async def test_logic():
        engine, session, repo = await get_test_repo_and_session()
        lead_id = None
        try:
            new_lead = LinkedInLead(full_name="Update Test", linkedin_url=test_url)
            session.add(new_lead)
            await session.commit()
            lead_id = new_lead.id
            
            # 1. Test update_dm_sent
            await repo.update_dm_sent(lead_id)
            
            # Refresh from DB
            updated = await repo.get_by_id(lead_id)
            assert updated["is_dm_sent"] == True
            assert updated["dm_sent_at"] is not None
            
            # 2. Test update_ai_enrichment
            ai_vars = {"test": "data"}
            await repo.update_ai_enrichment(
                lead_id=lead_id,
                hiring_signal=True,
                hiring_roles="DevOps",
                pain_points="Scale",
                ai_variables=ai_vars,
                linkedin_dm="Hello!"
            )
            
            final_lead = await repo.get_by_id(lead_id)
            assert final_lead["hiring_signal"] == True
            assert final_lead["hiring_roles"] == "DevOps"
            assert final_lead["linkedin_dm"] == "Hello!"
            assert final_lead["ai_variables"] == ai_vars
            
        finally:
            await cleanup(engine, session, lead_id)
            
    asyncio.run(test_logic())

def test_repo_keyword_filtering():
    """
    Verify JSONB keyword filtering (get_all_leads and get_total_count).
    """
    test_url = generate_unique_url()
    kw = f"unique_kw_{uuid.uuid4().hex[:4]}"
    
    async def test_logic():
        engine, session, repo = await get_test_repo_and_session()
        lead_id = None
        try:
            # Lead with a specific keyword in post_data array
            post_data = [{"search_keyword": kw, "text": "We are hiring!"}]
            new_lead = LinkedInLead(
                full_name="Filter Test", 
                linkedin_url=test_url,
                post_data=post_data
            )
            session.add(new_lead)
            await session.commit()
            lead_id = new_lead.id
            
            # 1. Test get_total_count with keyword
            count = await repo.get_total_count(keyword=kw)
            assert count == 1
            
            # 2. Test get_all_leads with keyword
            leads = await repo.get_all_leads(keyword=kw)
            assert len(leads) == 1
            assert leads[0]["full_name"] == "Filter Test"
            
            # 3. Test filter with non-existent keyword
            empty_count = await repo.get_total_count(keyword="nonexistent")
            assert empty_count == 0
            
        finally:
            await cleanup(engine, session, lead_id)
            
    asyncio.run(test_logic())

def test_repo_get_unique_keywords():
    """
    Verify extraction of unique keywords from JSONB array.
    """
    u1 = generate_unique_url()
    u2 = generate_unique_url()
    kw1 = f"kw1_{uuid.uuid4().hex[:4]}"
    kw2 = f"kw2_{uuid.uuid4().hex[:4]}"
    
    async def test_logic():
        engine, session, repo = await get_test_repo_and_session()
        ids = []
        try:
            l1 = LinkedInLead(full_name="L1", linkedin_url=u1, post_data=[{"search_keyword": kw1}])
            l2 = LinkedInLead(full_name="L2", linkedin_url=u2, post_data=[{"search_keyword": kw1}, {"search_keyword": kw2}])
            session.add_all([l1, l2])
            await session.commit()
            ids = [l1.id, l2.id]
            
            # Test unique keywords extraction
            keywords = await repo.get_unique_keywords()
            assert kw1 in keywords
            assert kw2 in keywords
            
        finally:
            for lid in ids:
                await session.execute(text("DELETE FROM linkedin_outreach_leads WHERE id = :id"), {"id": lid})
            await session.commit()
            await cleanup(engine, session)
            
    asyncio.run(test_logic())
