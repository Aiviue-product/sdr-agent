import logging
from sqlalchemy import text
from app.db.session import AsyncSessionLocal  

logger = logging.getLogger("lead_service")

async def save_verified_leads_to_db(df):
    """
    Saves ONLY valid, fully populated leads to Postgres.
    Expects standardized lowercase keys from file_service.
    """
    logger.info(f"💾 Processing {len(df)} rows for database storage...")

    leads_to_save = []
    skipped_count = 0

    for index, row in df.iterrows():
        # 1. Verification Check (Keys are already lowercase)
        status = str(row.get('status', '')).lower()
        tag = str(row.get('tag', ''))
        
        # Only save valid/Verified leads
        if status != 'valid' or tag != 'Verified':
            skipped_count += 1
            continue

        # 2. Extract Data using STANDARD LOWERCASE KEYS
        email = row.get('email')
        first_name = row.get('firstname')
        company = row.get('company_name')
        linkedin = row.get('linkedin_url')
        mobile = row.get('mobile_number')
        
        # Keys updated to lowercase based on your new logic
        designation = row.get('designation') 
        sector = row.get('sector')
        priority = row.get('priority')

        # 3. Validation: Check for empty/NaN values
        required_fields = [email, first_name, company, linkedin, mobile, designation, sector]
        
        # Helper to check if a value is effectively empty
        if any(not str(f).strip() or str(f).lower() == 'nan' for f in required_fields):
            logger.warning(f"⚠️ Skipping {email}: Missing required fields.")
            skipped_count += 1
            continue

        # 4. Prepare Record for DB
        leads_to_save.append({
            "email": str(email).strip(),
            "first_name": str(first_name).strip(),
            "last_name": str(row.get('lastname', '')).strip(), # Optional
            "company_name": str(company).strip(),
            "linkedin_url": str(linkedin).strip(),
            "mobile_number": str(mobile).strip(),
            "designation": str(designation).strip(),
            "sector": str(sector).strip(),
            "priority": str(priority).strip(),
            "verification_status": status,
            "verification_tag": tag
        })

    if not leads_to_save:
        logger.info("ℹ️ No leads met the strict criteria to be saved.")
        return

    # 5. Batch Upsert to DB
    async with AsyncSessionLocal() as session:
        try:
            for lead in leads_to_save:
                # SQL Query
                query = text("""
                    INSERT INTO leads (
                        email, first_name, last_name, company_name, linkedin_url, mobile_number, 
                        designation, sector, priority, verification_status, verification_tag
                    )
                    VALUES (
                        :email, :first_name, :last_name, :company_name, :linkedin_url, :mobile_number, 
                        :designation, :sector, :priority, :verification_status, :verification_tag
                    )
                    ON CONFLICT (email) 
                    DO UPDATE SET 
                        verification_status = EXCLUDED.verification_status,
                        verification_tag = EXCLUDED.verification_tag,
                        designation = EXCLUDED.designation,
                        sector = EXCLUDED.sector,
                        priority = EXCLUDED.priority,
                        updated_at = NOW();
                """)
                await session.execute(query, lead)
            
            await session.commit()
            logger.info(f"✅ Successfully saved {len(leads_to_save)} leads to Postgres. (Skipped: {skipped_count})")
            
        except Exception as e:
            await session.rollback()
            logger.error(f"❌ Database Error: {e}")