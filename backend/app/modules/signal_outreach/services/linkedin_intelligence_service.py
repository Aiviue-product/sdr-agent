"""
LinkedIn Intelligence Service
Analyzes LinkedIn posts for hiring signals and generates personalized DMs.
Uses Google Gemini AI for natural language processing.
"""
from google import genai
import os
import json
import asyncio
import logging
from typing import Optional
from app.shared.core.constants import TIMEOUT_GEMINI_AI, GEMINI_MODEL_NAME

logger = logging.getLogger("linkedin_intelligence_service")


class LinkedInIntelligenceService:
    """
    AI service for analyzing LinkedIn posts and generating personalized DMs.
    
    Two main functions:
    1. analyze_post() - Extract hiring signals, roles, pain points
    2. generate_dm() - Create personalized LinkedIn DM message
    """
    
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.warning("GEMINI_API_KEY is missing in environment variables.")
        self.client = genai.Client(api_key=api_key)
        self.model_name = GEMINI_MODEL_NAME

    async def analyze_and_generate_dm(
        self, 
        post_data: dict, 
        author_name: str,
        author_headline: Optional[str] = None
    ) -> dict:
        """
        Combined analysis: Analyze post AND generate personalized DM in one call.
        More efficient than separate calls.
        
        Args:
            post_data: Full post object from Apify (contains 'text', 'hashtags', etc.)
            author_name: Name of the post author
            author_headline: Author's LinkedIn headline (optional)
            
        Returns:
            dict with hiring_signal, hiring_roles, pain_points, ai_variables, linkedin_dm
        """
        post_text = post_data.get("text", "") or post_data.get("content", {}).get("text", "")
        hashtags = post_data.get("hashtags", [])
        posted_at = post_data.get("posted_at", {}).get("date", "recently")
        
        if not post_text:
            return self._get_fallback_analysis(author_name)

        # Build prompt for combined analysis + DM generation
        prompt = f"""
Act as a Senior SDR (Sales Development Representative) who specializes in LinkedIn outreach.
Your task is to analyze a LinkedIn post and create a personalized connection message.

=== POST DATA ===
Author: {author_name}
Headline: {author_headline or 'Not available'}
Posted: {posted_at}
Hashtags: {', '.join(hashtags) if hashtags else 'None'}

Post Content:
\"\"\"{post_text[:1500]}\"\"\"

=== YOUR TASK ===
Analyze this post and provide TWO things:

1. ANALYSIS - Determine:
   - Is this a HIRING post? (company actively looking to hire)
   - What specific roles are they hiring for?
   - What pain points might they have?
   
   IMPORTANT: Return hiring_signal=FALSE if:
   - The author is looking for a job (job seeker, not hiring)
   - The author just joined a company
   - This is just a thought leadership post with no hiring intent

2. PERSONALIZED DM - Write a short LinkedIn connection message that:
   - Uses a casual professional tone (like a friendly colleague)
   - References something SPECIFIC from their post
   - Is under 300 characters (LinkedIn limit for connection requests)
   - Has a clear but soft call-to-action
   - Does NOT sound salesy or spammy
   - Does NOT use phrases like "I hope this finds you well"
   
   Good examples:
   - "Hi {{name}}! Saw your post about hiring CNC operators in Punjab. We help manufacturing companies source skilled operators faster - would love to connect!"
   - "Hey {{name}} 👋 Your post about scaling the tech team resonated with me. We work with startups on their hiring challenges. Open to connecting?"

=== OUTPUT FORMAT ===
Return ONLY valid JSON (no markdown, no explanation):
{{
    "hiring_signal": true/false,
    "hiring_roles": "Role 1, Role 2" or "" if not hiring,
    "pain_points": "Brief description of likely challenge",
    "key_competencies": "Skills/tools mentioned",
    "standardized_persona": "HR / TA" or "Founder" or "Recruiter" or "Operations" or "Tech" or "Other",
    "linkedin_dm": "Your personalized DM message here (max 300 chars)"
}}
"""

        try:
            response = await asyncio.wait_for(
                self.client.aio.models.generate_content(
                    model=self.model_name,
                    contents=prompt
                ),
                timeout=TIMEOUT_GEMINI_AI
            )
            
            # Parse response
            raw_text = response.text.replace("```json", "").replace("```", "").strip()
            analysis = json.loads(raw_text)
            
            # Ensure all required fields exist
            return {
                "hiring_signal": analysis.get("hiring_signal", False),
                "hiring_roles": analysis.get("hiring_roles", ""),
                "pain_points": analysis.get("pain_points", ""),
                "ai_variables": analysis,  # Store full response
                "linkedin_dm": analysis.get("linkedin_dm", self._get_fallback_dm(author_name))
            }

        except asyncio.TimeoutError:
            logger.error(f"AI Analysis timed out (>{TIMEOUT_GEMINI_AI}s)")
            return self._get_fallback_analysis(author_name)
        except json.JSONDecodeError as e:
            logger.error(f"AI returned invalid JSON: {e}")
            return self._get_fallback_analysis(author_name)
        except Exception as e:
            logger.error(f"AI Analysis Failed: {e}")
            return self._get_fallback_analysis(author_name)

    async def analyze_post(self, post_data: dict, author_name: str) -> dict:
        """
        Analyze a single post for hiring signals (without DM generation).
        Useful for batch analysis where DM isn't needed yet.
        """
        # Call the combined function but focus on analysis
        result = await self.analyze_and_generate_dm(post_data, author_name)
        return {
            "hiring_signal": result["hiring_signal"],
            "hiring_roles": result["hiring_roles"],
            "pain_points": result["pain_points"],
            "ai_variables": result["ai_variables"]
        }

    async def generate_dm(
        self, 
        post_data: dict, 
        author_name: str,
        hiring_roles: Optional[str] = None,
        pain_points: Optional[str] = None
    ) -> str:
        """
        Generate just the DM message (when analysis already exists).
        """
        post_text = post_data.get("text", "")[:500]
        
        prompt = f"""
Write a short LinkedIn connection message (max 300 chars) to {author_name}.

Context from their post:
\"\"\"{post_text}\"\"\"

{f"They are hiring for: {hiring_roles}" if hiring_roles else ""}
{f"Their likely challenge: {pain_points}" if pain_points else ""}

Requirements:
- Casual professional tone
- Reference something specific from their post
- Soft call-to-action
- NO "I hope this finds you well"
- Under 600 characters

Return ONLY the message text, nothing else.
"""

        try:
            response = await asyncio.wait_for(
                self.client.aio.models.generate_content(
                    model=self.model_name,
                    contents=prompt
                ),
                timeout=TIMEOUT_GEMINI_AI
            )
            
            dm = response.text.strip().strip('"').strip("'")
            return dm[:300]  # Ensure under limit
            
        except Exception as e:
            logger.error(f"DM Generation Failed: {e}")
            return self._get_fallback_dm(author_name)

    def _get_fallback_analysis(self, author_name: str) -> dict:
        """Returns safe default values if AI fails"""
        first_name = author_name.split()[0] if author_name else "there"
        return {
            "hiring_signal": False,
            "hiring_roles": "",
            "pain_points": "General hiring and talent challenges",
            "ai_variables": {},
            "linkedin_dm": self._get_fallback_dm(first_name)
        }

    def _get_fallback_dm(self, author_name: str) -> str:
        """Generic fallback DM if AI fails"""
        first_name = author_name.split()[0] if author_name else "there"
        return f"Hi {first_name}! Came across your LinkedIn profile and would love to connect. Always great to expand the network with professionals in similar spaces!"


# Singleton instance for easy import
linkedin_intelligence_service = LinkedInIntelligenceService()
