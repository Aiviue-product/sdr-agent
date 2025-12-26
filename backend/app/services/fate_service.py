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
        Combines Lead Dict + FATE Row -> 3 Filled Emails.
        NOW SUPPORTS: AI Variables from Enrichment.
        """
        if not fate_rule:
            return None

        # 1. Get AI Variables
        ai_vars = lead_data.get("ai_variables") or {}
        
        # 2. DETERMINE THE OPENING LINE (The Logic Fix)
        # Check if we have a personalized intro saved
        intro_hook = lead_data.get("personalized_intro")
        company = lead_data.get("company_name", "your company")
        
        # If AI hook exists, use it. Otherwise, use the Generic fallback.
        if intro_hook:
            opening_line = intro_hook
        else:
            opening_line = f"Saw you're leading things at {company}."

        # 3. Prepare Context
        context = {
            # Basic Info
            "first_name": lead_data.get("first_name", "there"),
            "company_name": company,
            
            # THE NEW DYNAMIC OPENER
            "opening_line": opening_line,

            # FATE Matrix Rules
            "sector": fate_rule.sector,
            "f_pain": fate_rule.f_pain,
            "a_goal": fate_rule.a_goal,
            "t_solution": fate_rule.t_solution,
            "e_evidence": fate_rule.e_evidence,
            "urgency_level": fate_rule.urgency_level,

            # AI Enriched Variables (Fallbacks included)
            "hiring_roles": ai_vars.get("hiring_roles", "key roles"),
            "key_competencies": ai_vars.get("key_competencies", "critical skills"),
            "pain_points": ai_vars.get("pain_points", fate_rule.f_pain)
        }

        # 4. Generate the 3 variations
        generated = {}
        
        # Template 1: Pain Led (Uses {opening_line})
        t1 = EMAIL_TEMPLATES["pain_led"]
        generated["email_1"] = {
            "subject": t1["subject"].format(**context),
            "body": t1["body"].format(**context)
        }

        # Template 2: Case Reinforcement
        t2 = EMAIL_TEMPLATES["case_reinforcement"]
        generated["email_2"] = {
            "subject": t2["subject"].format(**context),
            "body": t2["body"].format(**context)
        }

        # Template 3: Direct Ask
        t3 = EMAIL_TEMPLATES["direct_ask"]
        generated["email_3"] = {
            "subject": t3["subject"].format(**context),
            "body": t3["body"].format(**context)
        }

        return generated

async def generate_emails_for_lead(lead_id: int):
    """
    Orchestrator function.
    """
    async with AsyncSessionLocal() as session:
        # A. Fetch Lead
        query_lead = text("SELECT * FROM leads WHERE id = :id")
        result = await session.execute(query_lead, {"id": lead_id})
        lead = result.mappings().first()

        if not lead:
            return {"error": "Lead not found"}

        # B. Get FATE Rule
        generator = FateEmailGenerator(session)
        fate_rule = await generator.get_fate_rule(lead.sector, lead.designation)

        if not fate_rule:
            return {"error": f"No FATE rule found for Sector: {lead.sector}"}

        # C. Generate Content
        # We pass the full lead dict (which has 'personalized_intro') into fill_templates
        # The logic for placing the hook is now handled INSIDE fill_templates
        emails = generator.fill_templates(dict(lead), fate_rule)

        # D. Save to DB
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