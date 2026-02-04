import logging
import pandas as pd # Ensure pandas is imported
from app.shared.db.session import AsyncSessionLocal
from app.modules.email_outreach.repositories.lead_repository import LeadRepository

logger = logging.getLogger("lead_service")

async def save_verified_leads_to_db(df):
    """
    Saves leads to database based on verification status:
    - 'valid' emails -> lead_stage = 'campaign' (ready for outreach)
    - 'invalid', 'catch-all', 'api_error' -> lead_stage = 'email_enrichment' (needs email correction)
    - 'skipped_low_priority' -> NOT saved (intentionally filtered out)
    """
    logger.info(f"💾 Processing {len(df)} rows for database storage...")

    leads_to_save = []
    skipped_count = 0
    email_enrichment_count = 0

    for index, row in df.iterrows():
        # 1. Verification Check - Determine lead_stage based on status
        status = str(row.get('status', '')).lower()
        
        # Determine lead_stage based on verification status
        if status == 'valid':
            lead_stage = 'campaign'  # Valid email → Campaign ready
        elif status in ['invalid', 'catch-all', 'api_error']:
            lead_stage = 'email_enrichment'  # Bad/unverified email → Needs email enrichment
            email_enrichment_count += 1
        else:
            # Skip low priority leads (they're intentionally filtered out)
            skipped_count += 1
            continue

        # 2. Clean Data Helper
        # Converts "nan", "NaN", or whitespace to Python None (SQL NULL)
        def clean(val):
            s = str(val).strip()
            return None if not s or s.lower() == 'nan' else s

        # 3. Extract Data
        email = clean(row.get('email'))
        
        # STRICT: Email is the only hard requirement
        if not email:
            logger.warning(f"⚠️ Row {index}: Skipped - No Email Address.")
            skipped_count += 1
            continue

        first_name = clean(row.get('firstname'))
        company = clean(row.get('company_name'))
        linkedin = clean(row.get('linkedin_url'))
        mobile = clean(row.get('mobile_number'))
        designation = clean(row.get('designation'))
        sector = clean(row.get('sector'))
        priority = clean(row.get('priority'))
        tag = str(row.get('tag', ''))

        # 4. Prepare Record
        leads_to_save.append({  
            "email": email,
            "first_name": first_name,
            "last_name": clean(row.get('lastname')),
            "company_name": company,
            "linkedin_url": linkedin,
            "mobile_number": mobile,
            "designation": designation,
            "sector": sector,
            "priority": priority,
            "verification_status": status, 
            "verification_tag": tag,
            "lead_stage": lead_stage 
        })

    if not leads_to_save:
        logger.info("ℹ️ No leads found to save.")
        return

    # 5. Batch Upsert to DB (via repository)
    async with AsyncSessionLocal() as session:
        try:
            lead_repo = LeadRepository(session)
            await lead_repo.bulk_upsert_leads(leads_to_save)
            campaign_count = len(leads_to_save) - email_enrichment_count
            logger.info(f"✅ Saved {len(leads_to_save)} leads to DB: {campaign_count} to Campaign, {email_enrichment_count} to Email Enrichment.")
            
        except Exception as e:
            await session.rollback()
            logger.error(f"❌ Database Error: {e}")  
