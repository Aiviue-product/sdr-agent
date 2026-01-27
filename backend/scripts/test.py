# In Python shell with venv activated
import asyncio
from app.modules.signal_outreach.services import linkedin_search_service

async def test():
    result = await linkedin_search_service.search_by_keywords(
        keywords=["hiring software engineer"],
        date_filter="past-week",
        posts_per_keyword=5
    )
    print(f"Found {result['stats']['unique_leads']} leads")
    for lead in result['leads'][:2]:
        print(f"  - {lead['full_name']} ({lead['linkedin_url']})")

asyncio.run(test()) 