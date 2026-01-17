import asyncio
import os
import sys
from datetime import datetime
from sqlalchemy import create_all, select, delete
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from dotenv import load_dotenv

# Add backend to path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.modules.signal_outreach.models.linkedin_lead import LinkedInLead
from app.modules.signal_outreach.models.linkedin_activity import LinkedInActivity

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# Disable prepared statements for PgBouncer compatibility
engine = create_async_engine(
    DATABASE_URL, 
    connect_args={
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0
    }
)
async_session = async_sessionmaker(engine, expire_on_commit=False)

async def inject_new_connection_lead():
    print("🚀 Injecting NEW CONNECTION test lead into database...")
    
    # CHANGE THIS to a LinkedIn URL of someone you are NOT connected with
    # Use a dummy account or a colleague's account for testing
    lead_url = "https://www.linkedin.com/in/some-new-lead-url/" 
    
    async with async_session() as session:
        # 1. Clean up existing test lead if it exists
        await session.execute(delete(LinkedInLead).where(LinkedInLead.linkedin_url == lead_url))
        await session.commit()

        # 2. Add as a fresh lead with no connection
        new_lead = LinkedInLead(
            full_name="New Connection Test",
            linkedin_url=lead_url,
            headline="Future Connection | Testing Auto-DM",
            search_keyword="New-Connection-Test",
            hiring_signal=True,
            hiring_roles="Software Engineer",
            pain_points="Testing if the Auto-DM fires upon connection acceptance.",
            linkedin_dm="Hi! This is an AUTO-DM. I'm testing the real-time connection acceptance trigger. Did this work?",
            connection_status='none', # Important: Start as none
            is_dm_sent=False,
            dm_status='not_sent'
        )
        
        session.add(new_lead)
        await session.commit()
        await session.refresh(new_lead)
        
        print(f"✅ Successfully injected lead: {new_lead.full_name}")
        print(f"🆔 Database ID: {new_lead.id}")
        print("-" * 50)
        print("TEST STEPS:")
        print(f"1. Open your dashboard and find '{new_lead.full_name}'.")
        print("2. CHANGE THE URL in this script line 34 if needed, then re-run it.")
        print("3. Click the 'Connect' button in the dashboard.")
        print("4. Go to the LinkedIn account for this lead and ACCEPT the connection.")
        print("5. WAIT: Check your server terminal for 'new_relation' webhook.")
        print("6. VERIFY: The server should automatically trigger 'create_chat_and_send_dm' right after acceptance!")
        print("-" * 50)

if __name__ == "__main__":
    asyncio.run(inject_new_connection_lead())
