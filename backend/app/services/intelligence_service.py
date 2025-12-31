from google import genai
import os
import json
import logging

logger = logging.getLogger("intelligence_service")

class IntelligenceService:
    def __init__(self):
        # 1. Initialize Client with New SDK
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))   
        self.model_name = 'gemini-2.5-flash'

    async def analyze_profile(self, scraped_data: list):
        """
        Input: List of dicts (posts, designation, etc.) from Scraper Service.
        Output: Structured JSON with industry-agnostic signals.
        """
        if not scraped_data:
            return self._get_fallback_analysis()

        # 2. Prepare Context
        context_text = ""
        for item in scraped_data[:5]: 
            context_text += f"\n--- Post ({item['date']}) ---\n"
            context_text += f"Author Role: {item['designation']}\n"
            context_text += f"Content: {item['post_text']}\n"

        # 3. Industry-Agnostic Prompt
        prompt = f"""
        Act as a Senior B2B Market Researcher. Analyze the following LinkedIn activity for a potential lead.
        The lead could be from ANY industry (Tech, Automotive, Microfinance, Logistics, QSR, Retail, etc.).

        DATA:
        {context_text}

        TASK:
        Extract insights into a valid JSON object. Be specific to their industry context.

        JSON KEYS TO EXTRACT:
        1. "hiring_signal" (Boolean): 
           - True ONLY if THE COMPANY/ORGANIZATION is ACTIVELY SEEKING to hire new employees.
           - Look for phrases like: "we're hiring", "join our team", "open positions", "looking for candidates", "expanding our team", "recruiting for".
           - If "hiring" is mentioned as a product/service description (e.g., "we are a hiring platform")
           IMPORTANT - Return FALSE in these cases:
           - If the AUTHOR is announcing THEY GOT HIRED or JOINED a company (e.g., "I've joined XYZ as an intern")
           - If the post is about the author's job search journey or interview experiences
           - If there's no clear indication the company has open roles RIGHT NOW
        
        2. "hiring_roles" (String): 
           - Comma-separated roles THE COMPANY is actively looking to fill.
           - Only populate if hiring_signal is True.
           - If Tech: "React Dev, DevOps"
           - If Retail/Ops: "Store Managers, Delivery Riders, Area Sales Manager"
           - If Finance: "Accountants, Branch Managers"
           - If hiring_signal is False: Return empty string "".

        3. "key_competencies" (String): 
           - List the hard skills, tools, or methodologies they value or mention.
           - Tech: "AWS, Python, CI/CD"
           - HR/Admin: "Excel, Compliance, Employee Relations, Payroll"
           - Ops/Logistics: "Supply Chain, Fleet Management, SAP, Cost Reduction"
           - Finance: "Auditing, Tally, P&L Management, GST"

        4. "pain_points" (String): 
           - Infer 1 key business challenge they are likely facing based on their content or role.
           - Examples: "Reducing staff attrition", "Optimizing last-mile delivery", "Regulatory compliance", "Scaling cloud infra".

        5. "standardized_persona" (String): 
           - Classify them into one of these buckets based on their role:
           - "Founder", "HR / TA", "Ops / COO", "Branch / Regional Mgr", "Tech / Engineering", "Sales / Marketing", or "Other".

        6. "summary_hook" (String): 
           - Write a highly natural human tone, 1-sentence email opener referencing their specific recent activity or focus.
           - Rule: Do NOT be cringe. Do NOT say "I hope you are well".
           - Example: "Saw you're expanding the logistics team in the Mumbai region."
           - Example: "Loved your point about the importance of empathy in HR leadership."

        OUTPUT JSON ONLY:
        """

        try:
            # 4. Call Gemini (New Async Syntax: client.aio.models.generate_content)
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            
            # The new SDK response object has a .text attribute directly
            raw_text = response.text.replace("```json", "").replace("```", "").strip()
            
            # 5. Parse JSON
            analysis = json.loads(raw_text)
            return analysis

        except Exception as e:
            logger.error(f"❌ AI Analysis Failed: {e}")
            return self._get_fallback_analysis()

    def _get_fallback_analysis(self):
        """Returns safe default values if AI fails"""
        return {
            "hiring_signal": False,
            "hiring_roles": "",
            "key_competencies": "General Management",
            "pain_points": "Operational Efficiency",
            "standardized_persona": "Other",
            "summary_hook": "Hope you're having a productive week."
        }

intelligence_service = IntelligenceService() 