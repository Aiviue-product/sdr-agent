import logging
import pandas as pd # Ensure pandas is imported
from sqlalchemy import text
from app.db.session import AsyncSessionLocal  

logger = logging.getLogger("lead_service")

async def save_verified_leads_to_db(df):
    """
    Saves ALL verified leads.
    - Fully populated -> marked as 'campaign'
    - Missing fields  -> marked as 'enrichment'
    """
    logger.info(f"💾 Processing {len(df)} rows for database storage...")

    leads_to_save = []
    skipped_count = 0

    for index, row in df.iterrows():
        # 1. Verification Check
        status = str(row.get('status', '')).lower()
        if status != 'valid':
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

        # 4. DETERMINE LEAD STAGE (The New Logic)
        # Check if critical fields are missing
        # You can adjust this list based on what you consider "Campaign Ready"
        required_for_campaign = [company, linkedin, mobile, designation, sector]
        
        if any(field is None for field in required_for_campaign):
            lead_stage = 'enrichment'  # Valid email, but missing details
        else:
            lead_stage = 'campaign'    # Ready for outreach

        # 5. Prepare Record
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
        logger.info("ℹ️ No verified leads found to save.")
        return

    # 6. Batch Upsert to DB
    async with AsyncSessionLocal() as session:
        try:
            for lead in leads_to_save:
                # We added 'lead_stage' to the INSERT and UPDATE parts
                query = text("""
                    INSERT INTO leads (
                        email, first_name, last_name, company_name, linkedin_url, mobile_number, 
                        designation, sector, priority, verification_status, verification_tag, lead_stage
                    )
                    VALUES (
                        :email, :first_name, :last_name, :company_name, :linkedin_url, :mobile_number, 
                        :designation, :sector, :priority, :verification_status, :verification_tag, :lead_stage
                    )
                    ON CONFLICT (email) 
                    DO UPDATE SET 
                        verification_status = EXCLUDED.verification_status,
                        verification_tag = EXCLUDED.verification_tag,
                        lead_stage = EXCLUDED.lead_stage,
                        
                        -- Smart Updates: Don't overwrite existing data with NULLs if new file is empty
                        company_name = COALESCE(EXCLUDED.company_name, leads.company_name),
                        linkedin_url = COALESCE(EXCLUDED.linkedin_url, leads.linkedin_url),
                        mobile_number = COALESCE(EXCLUDED.mobile_number, leads.mobile_number),
                        designation = COALESCE(EXCLUDED.designation, leads.designation),
                        sector = COALESCE(EXCLUDED.sector, leads.sector),
                        
                        updated_at = NOW();
                """)
                await session.execute(query, lead)
            
            await session.commit()
            logger.info(f"✅ Saved {len(leads_to_save)} leads to DB (Campaign + Enrichment).")
            
        except Exception as e:
            await session.rollback()
            logger.error(f"❌ Database Error: {e}")  