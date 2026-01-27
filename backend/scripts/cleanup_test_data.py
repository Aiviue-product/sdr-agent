import asyncio
import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from dotenv import load_dotenv

load_dotenv()

async def cleanup():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL not found")
        return

    # Use the same engine settings as the app for compatibility
    engine = create_async_engine(
        database_url, 
        echo=True,
        connect_args={"statement_cache_size": 0, "prepared_statement_cache_size": 0}
    )

    delete_queries = [
        # 1. Delete by Name patterns used in tests
        "DELETE FROM linkedin_outreach_leads WHERE full_name IN ('L1', 'L2', 'User 1', 'User 2', 'Test User', 'Update Test', 'Filter Test')",
        
        # 2. Delete by test URL pattern
        "DELETE FROM linkedin_outreach_leads WHERE linkedin_url LIKE 'https://linkedin.com/in/test_%'",
        
        # 3. Delete based on test keywords inside JSONB array
        """DELETE FROM linkedin_outreach_leads 
           WHERE EXISTS (
               SELECT 1 FROM jsonb_array_elements(post_data) AS post 
               WHERE post->>'search_keyword' LIKE 'kw1_%' 
                  OR post->>'search_keyword' LIKE 'kw2_%'
                  OR post->>'search_keyword' LIKE 'unique_kw_%'
           )"""
    ]

    async with engine.begin() as conn:
        for query in delete_queries:
            result = await conn.execute(text(query))
            print(f"Executed: {query[:50]}... | Rows affected: {result.rowcount}")

    await engine.dispose()
    print("Cleanup complete!")

if __name__ == "__main__":
    asyncio.run(cleanup())
