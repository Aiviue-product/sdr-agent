"""
LinkedIn Intelligence Service
Analyzes LinkedIn posts for hiring signals and generates personalized DMs.
Uses Google Gemini AI for natural language processing.

OPTIMIZATIONS:
- Regex-based JSON parsing (robust against markdown wrapping)
- Safe initialization (no crash if API key missing)
- XML delimiters to prevent prompt injection
- Structured prompting with clear tags
- Separate methods to save tokens
- JSON mode enforcement where supported
"""
from google import genai
from google.genai import types
import os
import re
import json
import asyncio
import logging
from typing import Optional
from app.shared.core.constants import TIMEOUT_GEMINI_AI, GEMINI_MODEL_NAME

logger = logging.getLogger("linkedin_intelligence_service")


def extract_json_from_response(text: str) -> dict:
    """
    Robustly extract JSON from AI response.
    Handles cases where AI wraps JSON in markdown or adds conversational text.
    
    Strategy:
    1. Find the first '{' and last '}' in the response
    2. Extract and parse that substring
    """
    if not text:
        return {}
    
    # Find first '{' and last '}'
    first_brace = text.find('{')
    last_brace = text.rfind('}')
    
    if first_brace == -1 or last_brace == -1 or first_brace >= last_brace:
        logger.warning("No valid JSON object found in response")
        return {}
    
    json_str = text[first_brace:last_brace + 1]
    
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing failed: {e}")
        # Try to fix common issues
        # Remove any trailing commas before } or ]
        json_str = re.sub(r',\s*([}\]])', r'\1', json_str)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            return {}


def sanitize_for_xml(text: str) -> str:
    """
    Sanitize text for safe inclusion in XML-style prompts.
    Escapes characters that could break XML parsing or enable injection.
    """
    if not text:
        return ""
    # Escape XML special characters
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    # Limit length to prevent token abuse
    return text[:2000]


class LinkedInIntelligenceService:
    """
    AI service for analyzing LinkedIn posts and generating personalized DMs.
    
    Two main functions:
    1. analyze_post() - Extract hiring signals, roles, pain points (no DM)
    2. generate_dm() - Create personalized LinkedIn DM message
    3. analyze_and_generate_dm() - Combined for efficiency when both needed
    """
    
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.client = None
        self.model_name = GEMINI_MODEL_NAME
        
        # Safe initialization - don't crash if key is missing
        if self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {e}")
                self.client = None
        else:
            logger.warning("GEMINI_API_KEY is missing - AI features will use fallbacks")

    def _is_available(self) -> bool:
        """Check if AI service is available"""
        return self.client is not None

    async def analyze_post(
        self, 
        post_data: dict, 
        author_name: str,
        author_headline: Optional[str] = None
    ) -> dict:
        """
        Analyze a LinkedIn post for hiring signals.
        Does NOT generate DM (saves tokens when DM not needed).
        
        Args:
            post_data: Full post object from Apify
            author_name: Name of the post author
            author_headline: Author's LinkedIn headline
            
        Returns:
            dict with hiring_signal, hiring_roles, pain_points, ai_variables
        """
        if not self._is_available():
            return self._get_fallback_analysis(author_name, include_dm=False)
        
        # Sanitize user data
        post_text = sanitize_for_xml(
            post_data.get("text", "") or post_data.get("content", {}).get("text", "")
        )
        hashtags = post_data.get("hashtags", [])
        posted_at = post_data.get("posted_at", {}).get("date", "recently")
        
        if not post_text:
            return self._get_fallback_analysis(author_name, include_dm=False)

        # Structured prompt with XML delimiters (ANALYSIS ONLY - no DM)
        prompt = f"""
<context>
You are analyzing a LinkedIn post to determine if the author is actively hiring.
</context>

<post_data>
<author_name>{sanitize_for_xml(author_name)}</author_name>
<author_headline>{sanitize_for_xml(author_headline or 'Not available')}</author_headline>
<posted_at>{sanitize_for_xml(str(posted_at))}</posted_at>
<hashtags>{sanitize_for_xml(', '.join(hashtags) if hashtags else 'None')}</hashtags>
<post_content>
{post_text}
</post_content>
</post_data>

<instructions>
Analyze the post and determine:

1. hiring_signal (boolean): Is this a HIRING post?
   - TRUE: Company is actively looking to hire (phrases like "we're hiring", "open positions", "join our team")
   - FALSE: Job seeker looking for work, someone announcing they joined a company, or just thought leadership

2. hiring_roles (string): What specific roles are they hiring for?
   - Only populate if hiring_signal is true
   - Format: "Role 1, Role 2, Role 3"
   - If not hiring, return empty string ""

3. pain_points (string): What business challenge might they have?
   - Brief description based on the post content

4. key_competencies (string): Skills or tools mentioned in the post

5. standardized_persona (string): Classify the author as one of:
   "HR / TA", "Founder", "Recruiter", "Operations", "Tech", "Sales / Marketing", "Other"
</instructions>

<output_format>
Return ONLY a valid JSON object with these exact keys:
{{
    "hiring_signal": true/false,
    "hiring_roles": "string",
    "pain_points": "string",
    "key_competencies": "string",
    "standardized_persona": "string"
}}
</output_format>
"""

        try:
            # Configure for JSON response
            config = types.GenerateContentConfig(
                response_mime_type="application/json"
            )
            
            response = await asyncio.wait_for(
                self.client.aio.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=config
                ),
                timeout=TIMEOUT_GEMINI_AI
            )
            
            # Robust JSON extraction
            analysis = extract_json_from_response(response.text)
            
            if not analysis:
                return self._get_fallback_analysis(author_name, include_dm=False)
            
            return {
                "hiring_signal": analysis.get("hiring_signal", False),
                "hiring_roles": analysis.get("hiring_roles", ""),
                "pain_points": analysis.get("pain_points", ""),
                "ai_variables": analysis
            }

        except asyncio.TimeoutError:
            logger.error(f"AI Analysis timed out (>{TIMEOUT_GEMINI_AI}s)")
            return self._get_fallback_analysis(author_name, include_dm=False)
        except Exception as e:
            logger.error(f"AI Analysis Failed: {e}")
            return self._get_fallback_analysis(author_name, include_dm=False)

    async def generate_dm(
        self, 
        post_data: dict, 
        author_name: str,
        hiring_roles: Optional[str] = None,
        pain_points: Optional[str] = None
    ) -> str:
        """
        Generate ONLY the DM message (when analysis already exists).
        Saves tokens by not re-analyzing the post.
        
        Args:
            post_data: Post object from Apify
            author_name: Name of the author
            hiring_roles: Pre-analyzed hiring roles (optional)
            pain_points: Pre-analyzed pain points (optional)
            
        Returns:
            str: Personalized DM message (max 300 chars)
        """
        if not self._is_available():
            return self._get_fallback_dm(author_name)
        
        post_text = sanitize_for_xml(post_data.get("text", "")[:500])
        first_name = author_name.split()[0] if author_name else "there"
        
        prompt = f"""
<context>
You are writing a LinkedIn connection request message. Keep it under 300 characters.
</context>

<recipient>
<name>{sanitize_for_xml(first_name)}</name>
<hiring_for>{sanitize_for_xml(hiring_roles or 'Not specified')}</hiring_for>
<likely_challenge>{sanitize_for_xml(pain_points or 'General')}</likely_challenge>
</recipient>

<their_post>
{post_text}
</their_post>

<instructions>
Write a short LinkedIn connection message that:
- Uses casual professional tone (like a friendly colleague)
- References something SPECIFIC from their post
- Is under 400 characters total
- Has a soft call-to-action
- Does NOT sound salesy or spammy
- Does NOT use "I hope this finds you well" or similar clichés
</instructions>

<output_format>
Return ONLY the message text. No quotes, no explanation, just the message.
</output_format>
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
            return dm[:400]  # Ensure under LinkedIn limit
            
        except Exception as e:
            logger.error(f"DM Generation Failed: {e}")
            return self._get_fallback_dm(author_name)

    async def analyze_and_generate_dm(
        self, 
        post_data: dict, 
        author_name: str,
        author_headline: Optional[str] = None
    ) -> dict:
        """
        Combined analysis: Analyze post AND generate personalized DM in one call.
        More efficient when both are needed.
        
        Args:
            post_data: Full post object from Apify
            author_name: Name of the post author
            author_headline: Author's LinkedIn headline
            
        Returns:
            dict with hiring_signal, hiring_roles, pain_points, ai_variables, linkedin_dm
        """
        if not self._is_available():
            return self._get_fallback_analysis(author_name, include_dm=True)
        
        # Sanitize user data
        post_text = sanitize_for_xml(
            post_data.get("text", "") or post_data.get("content", {}).get("text", "")
        )
        hashtags = post_data.get("hashtags", [])
        posted_at = post_data.get("posted_at", {}).get("date", "recently")
        first_name = author_name.split()[0] if author_name else "there"
        
        if not post_text:
            return self._get_fallback_analysis(author_name, include_dm=True)

        # Combined prompt with XML structure
        prompt = f"""
<context>
You are a Senior SDR analyzing a LinkedIn post and creating a personalized connection message.
</context>

<post_data>
<author_name>{sanitize_for_xml(author_name)}</author_name>
<author_first_name>{sanitize_for_xml(first_name)}</author_first_name>
<author_headline>{sanitize_for_xml(author_headline or 'Not available')}</author_headline>
<posted_at>{sanitize_for_xml(str(posted_at))}</posted_at>
<hashtags>{sanitize_for_xml(', '.join(hashtags) if hashtags else 'None')}</hashtags>
<post_content>
{post_text}
</post_content>
</post_data>

<instructions>
PART 1 - ANALYSIS:
Determine if this is a hiring post and extract key information.

hiring_signal: TRUE only if company is actively hiring. FALSE if:
- Author is a job seeker
- Author just joined a company
- Just thought leadership without hiring intent

PART 2 - DM MESSAGE:
Write a LinkedIn connection request message (under 300 chars) that:
- Uses casual professional tone
- References something specific from their post
- Has a soft call-to-action
- Does NOT sound salesy
- Does NOT use clichés like "I hope this finds you well"
</instructions>

<output_format>
Return ONLY valid JSON:
{{
    "hiring_signal": true/false,
    "hiring_roles": "Role 1, Role 2" or "",
    "pain_points": "Brief challenge description",
    "key_competencies": "Skills mentioned",
    "standardized_persona": "HR / TA" or "Founder" or "Recruiter" or "Operations" or "Tech" or "Other",
    "linkedin_dm": "Your personalized message here (max 400 chars)"
}}
</output_format>
"""

        try:
            config = types.GenerateContentConfig(
                response_mime_type="application/json"
            )
            
            response = await asyncio.wait_for(
                self.client.aio.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=config
                ),
                timeout=TIMEOUT_GEMINI_AI
            )
            
            # Robust JSON extraction
            analysis = extract_json_from_response(response.text)
            
            if not analysis:
                return self._get_fallback_analysis(author_name, include_dm=True)
            
            # Ensure DM is under limit
            dm = analysis.get("linkedin_dm", self._get_fallback_dm(author_name))
            if len(dm) > 300:
                dm = dm[:297] + "..."
            
            return {
                "hiring_signal": analysis.get("hiring_signal", False),
                "hiring_roles": analysis.get("hiring_roles", ""),
                "pain_points": analysis.get("pain_points", ""),
                "ai_variables": analysis,
                "linkedin_dm": dm
            }

        except asyncio.TimeoutError:
            logger.error(f"AI Analysis timed out (>{TIMEOUT_GEMINI_AI}s)")
            return self._get_fallback_analysis(author_name, include_dm=True)
        except Exception as e:
            logger.error(f"AI Analysis Failed: {e}")
            return self._get_fallback_analysis(author_name, include_dm=True)

    def _get_fallback_analysis(self, author_name: str, include_dm: bool = False) -> dict:
        """Returns safe default values if AI fails"""
        result = {
            "hiring_signal": False,
            "hiring_roles": "",
            "pain_points": "General hiring and talent challenges",
            "ai_variables": {}
        }
        
        if include_dm:
            result["linkedin_dm"] = self._get_fallback_dm(author_name)
        
        return result

    def _get_fallback_dm(self, author_name: str) -> str:
        """Generic fallback DM if AI fails"""
        first_name = author_name.split()[0] if author_name else "there"
        return f"Hi {first_name}! Came across your profile and would love to connect. Always great to expand the network with professionals in similar spaces!"


# Singleton instance for easy import
linkedin_intelligence_service = LinkedInIntelligenceService()
