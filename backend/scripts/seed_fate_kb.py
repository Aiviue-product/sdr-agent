import asyncio
import os
import sys
import logging

# Ensure we can find the app module
sys.path.append(os.path.join(os.path.dirname(__file__), '..')) 

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from dotenv import load_dotenv

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_kb")

# Load Env
load_dotenv()
DATABASE_URL = os.environ.get("DATABASE_URL")

# The FATE Matrix Data
KB_DATA = [
    {
        "sector": "Automotive", 
        "designation_role": "HR / TA",
        "f_pain": "Slow multi-location sourcing", 
        "a_goal": "Fast relevant candidates",
        "t_solution": "Curated + hyperlocal sourcing",  
        "e_evidence": "28 hires in 4 days",
        "urgency_level": "High"
    },
    {
        "sector": "Automotive", 
        "designation_role": "Ops / COO",
        "f_pain": "Vacancies delay operations", 
        "a_goal": "Fully staffed teams",
        "t_solution": "Rapid sourcing + screening", 
        "e_evidence": "Staffed 3 branches",
        "urgency_level": "Very High"
    },
    {
        "sector": "QSR", 
        "designation_role": "HR",
        "f_pain": "High churn + irrelevant walk-ins", 
        "a_goal": "Stable frontline pipeline",
        "t_solution": "Curated profile delivery", 
        "e_evidence": "Staffed 3 stores",
        "urgency_level": "Very High"
    },
    {
        "sector": "QSR", 
        "designation_role": "Area/Store Mgr",
        "f_pain": "Need daily replacements", 
        "a_goal": "Immediate local candidates",
        "t_solution": "Hyperlocal distribution", 
        "e_evidence": "12 hires in 3 days",
        "urgency_level": "Very High"
    },
    {
        "sector": "HR Consulting", 
        "designation_role": "Founder",
        "f_pain": "Pressure to close quickly", 
        "a_goal": "Reliable backend sourcing",
        "t_solution": "Volume curation", 
        "e_evidence": "Met SLAs",
        "urgency_level": "High"
    },
    {
        "sector": "Logistics", 
        "designation_role": "HR",
        "f_pain": "Hard to find warehouse workers", 
        "a_goal": "Steady worker supply", 
        "t_solution": "Local sourcing", 
        "e_evidence": "20 hires in 5 days",
        "urgency_level": "High"
    },
    {
        "sector": "Microfinance", 
        "designation_role": "HR / Cluster",
        "f_pain": "Field exec shortage", 
        "a_goal": "Stable field team", 
        "t_solution": "Rural sourcing", 
        "e_evidence": "Staffed 2 clusters",
        "urgency_level": "Very High"
    },
    {
        "sector": "Hospitality", 
        "designation_role": "HR / Ops",
        "f_pain": "Seasonal volume needs", 
        "a_goal": "High-volume pipeline", 
        "t_solution": "Distributed sourcing", 
        "e_evidence": "100+ hires supported",
        "urgency_level": "High"
    }
]

async def seed_kb():
    if not DATABASE_URL:
        logger.error("❌ DATABASE_URL is missing in .env")
        return

    logger.info(f"🔌 Connecting to DB to seed {len(KB_DATA)} rules...")
    
    # Create Engine
    engine = create_async_engine(DATABASE_URL)
    
    async with engine.begin() as conn:
        for entry in KB_DATA:
            # Upsert Logic: Insert, or Update if sector+role already exists
            query = text("""
                INSERT INTO fate_matrix (sector, designation_role, f_pain, a_goal, t_solution, e_evidence, urgency_level)
                VALUES (:sector, :designation_role, :f_pain, :a_goal, :t_solution, :e_evidence, :urgency_level)
                ON CONFLICT (sector, designation_role) 
                DO UPDATE SET 
                    f_pain = EXCLUDED.f_pain,
                    a_goal = EXCLUDED.a_goal,
                    t_solution = EXCLUDED.t_solution,
                    e_evidence = EXCLUDED.e_evidence,
                    urgency_level = EXCLUDED.urgency_level;
            """)
            await conn.execute(query, entry)
            logger.info(f"✅ Processed: {entry['sector']} -> {entry['designation_role']}")
            
    logger.info("✨ Knowledge Base Seeded Successfully!")
    await engine.dispose()

if __name__ == "__main__":
    # We use asyncio to run the async function
    asyncio.run(seed_kb()) 