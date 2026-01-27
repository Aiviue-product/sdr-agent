
import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

# Adjust these imports based on your exact file structure
from app.modules.signal_outreach.models.linkedin_lead import LinkedInLead
from app.shared.core.config import settings 

async def inject_connected_test_lead():
    print("🚀 Injecting ALREADY CONNECTED test lead into database...")
    
    # Setup database connection with PgBouncer compatibility
    engine = create_async_engine(
        settings.DATABASE_URL,
        connect_args={
            "statement_cache_size": 0,
            "prepared_statement_cache_size": 0
        }
    )
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    # CHANGE THIS to a LinkedIn URL of someone you are already connected with
    lead_url = "https://www.linkedin.com/in/sagar-rajak-032618289/" 
    
    async with async_session() as session:
        # Check if lead already exists
        result = await session.execute(select(LinkedInLead).where(LinkedInLead.linkedin_url == lead_url))
        existing_lead = result.scalar_one_or_none()
        
        if existing_lead:
            print(f"⚠️ Lead with URL {lead_url} already exists (ID: {existing_lead.id})")
            print("Cleaning up existing lead to re-inject fresh test data...")
            await session.delete(existing_lead)
            await session.commit()

        # Create new lead marked as ALREADY CONNECTED
        new_lead = LinkedInLead(
            full_name="Connected Test Lead",
            first_name="Connected",
            last_name="Test",
            linkedin_url=lead_url,
            headline="Already Connected | Testing Reply Webhooks",
            profile_image_url="https://api.dicebear.com/7.x/avataaars/svg?seed=Connected",
            search_keyword="Connected-Test",
            hiring_signal=True,
            hiring_roles="Software Engineer",
            pain_points="Testing if the reply webhook works in real-time.",
            ai_variables={
                "company_hiring": "Aiviue Labs",
                "summary_hook": "Testing our internal SDR reply detection."
            },
            linkedin_dm="Hi! I am testing the SDR agent reply detection. Can you message me back 'Test Success'?",
            connection_status='connected', # Setting as 'connected' so Send DM button is active
            is_dm_sent=False,
            dm_status='not_sent'
        )
        
        session.add(new_lead)
        await session.commit()
        await session.refresh(new_lead)
        
        print(f"✅ Successfully injected lead: {new_lead.full_name}")
        print(f"🆔 Database ID: {new_lead.id}")
        print("--------------------------------------------------")
        print("TEST STEPS:")
        print("1. Find 'Connected Test Lead' in your dashboard.")
        print("2. Click the green 'Send DM' button.")
        print("3. Check your server terminal - you should see 'DM sent successfully'.")
        print("4. IMPORTANT: Go to the LinkedIn account of this lead and REPLY to the message.")
        print("5. Watch your server terminal - you should see the [WEBHOOK] log for 'message_received'!")
        print("6. Open the 'Activity' timeline in our app to see the reply recorded.")
        print("--------------------------------------------------")

if __name__ == "__main__":
    asyncio.run(inject_connected_test_lead())
