import logging
from sqlalchemy import text
from app.db.session import AsyncSessionLocal
from app.core.templates import EMAIL_TEMPLATES 

logger = logging.getLogger("fate_service")

class FateEmailGenerator:
    def __init__(self, db_session):
        self.db = db_session

    async def get_fate_rule(self, sector: str, designation: str):
        """
        Tries to find a matching rule in the FATE Matrix.
        Logic:
        1. Try Exact Match (Sector + Designation)
        2. Fallback: Match Sector Only (Pick the first rule for that sector)
        """
        # 1. Try Exact Match
        query = text("""
            SELECT * FROM fate_matrix 
            WHERE LOWER(sector) = LOWER(:sector) 
            AND LOWER(designation_role) = LOWER(:designation)
            LIMIT 1;
        """)
        result = await self.db.execute(query, {"sector": sector, "designation": designation})
        rule = result.fetchone()

        if rule:
            return rule

        # 2. Fallback: Generic Sector Match
        # (If we don't know the specific role, we use the generic sector pain)
        logger.info(f"⚠️ No exact match for {designation} in {sector}. Using generic sector rule.")
        query_fallback = text("""
            SELECT * FROM fate_matrix 
            WHERE LOWER(sector) = LOWER(:sector) 
            LIMIT 1;
        """)
        result_fallback = await self.db.execute(query_fallback, {"sector": sector})
        return result_fallback.fetchone()

    def fill_templates(self, lead_data: dict, fate_rule) -> dict:
        """
        Combines Lead Dict + FATE Row -> 3 Filled Emails
        """
        if not fate_rule:
            return None

        # Prepare variables for the template
        # We perform a safe clean to avoid {company} errors if missing
        context = {
            "first_name": lead_data.get("first_name", "there"),
            "company_name": lead_data.get("company_name", "your company"),
            "sector": fate_rule.sector,
            "f_pain": fate_rule.f_pain,
            "a_goal": fate_rule.a_goal,
            "t_solution": fate_rule.t_solution,
            "e_evidence": fate_rule.e_evidence,
            "urgency_level": fate_rule.urgency_level
        }

        # Generate the 3 variations
        generated = {}
        
        # 1. Pain Led
        t1 = EMAIL_TEMPLATES["pain_led"]
        generated["email_1"] = {
            "subject": t1["subject"].format(**context),
            "body": t1["body"].format(**context)
        }

        # 2. Case Reinforcement
        t2 = EMAIL_TEMPLATES["case_reinforcement"]
        generated["email_2"] = {
            "subject": t2["subject"].format(**context),
            "body": t2["body"].format(**context)
        }

        # 3. Direct Ask
        t3 = EMAIL_TEMPLATES["direct_ask"]
        generated["email_3"] = {
            "subject": t3["subject"].format(**context),
            "body": t3["body"].format(**context)
        }

        return generated

async def generate_emails_for_lead(lead_id: int):
    """
    Orchestrator function to be called by API.
    1. Fetch Lead
    2. Find Rule
    3. Generate Emails
    4. Save to DB
    """
    async with AsyncSessionLocal() as session:
        # A. Fetch Lead
        query_lead = text("SELECT * FROM leads WHERE id = :id")
        lead_res = await session.execute(query_lead, {"id": lead_id})
        lead = lead_res.fetchone()

        if not lead:
            return {"error": "Lead not found"}

        # B. Get FATE Rule
        generator = FateEmailGenerator(session)
        fate_rule = await generator.get_fate_rule(lead.sector, lead.designation)

        if not fate_rule:
            return {"error": f"No FATE rule found for Sector: {lead.sector}"}

        # C. Generate Content
        # Convert SQLAlchemy row to dict for easier handling
        lead_dict = {
            "first_name": lead.first_name,
            "company_name": lead.company_name
        }
        
        emails = generator.fill_templates(lead_dict, fate_rule)

        # D. Save to DB (Hydrate the lead)
        update_query = text("""
            UPDATE leads 
            SET 
                email_1_body = :e1_body,
                email_2_body = :e2_body,
                email_3_body = :e3_body,
                updated_at = NOW()
            WHERE id = :id
        """)
        
        await session.execute(update_query, {
            "e1_body": emails["email_1"]["body"],
            "e2_body": emails["email_2"]["body"],
            "e3_body": emails["email_3"]["body"],
            "id": lead_id
        })
        await session.commit()
        
        return {"success": True, "emails": emails}