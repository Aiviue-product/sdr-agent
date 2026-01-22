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
- IMPROVED: Better hiring detection with keyword pre-check
- RATE LIMITING: Handles Gemini free tier (5 req/min) with delays and retries
"""
from google import genai
from google.genai import types
import os
import re
import json
import asyncio
import logging
import time
from typing import Optional, Tuple
from app.shared.core.constants import TIMEOUT_GEMINI_AI, GEMINI_MODEL_NAME

logger = logging.getLogger("linkedin_intelligence_service")


#TODO/sagar rajak: Add parallel processing support for when you upgrade

# ============================================
# RATE LIMITING CONFIGURATION
# ============================================
# Set GEMINI_TIER in .env to control rate limiting:
#   - "free"   : 5 req/min  → 13s delay between calls (default)
#   - "paid"   : 60 req/min → 1s delay between calls  
#   - "enterprise" : 1000+ req/min → no delay
GEMINI_TIER = os.getenv("GEMINI_TIER", "free").lower()

# Configure delays based on tier
if GEMINI_TIER == "enterprise":
    RATE_LIMIT_DELAY_SECONDS = 0
    ENABLE_PARALLEL = True
elif GEMINI_TIER == "paid":
    RATE_LIMIT_DELAY_SECONDS = 1  # 60 req/min limit
    ENABLE_PARALLEL = True
else:  # "free" or default
    RATE_LIMIT_DELAY_SECONDS = 13  # 5 req/min limit
    ENABLE_PARALLEL = False

MAX_RETRIES = 3
RETRY_BASE_DELAY_SECONDS = 60  # Start with 60s if we hit 429

logger.info(f"🤖 Gemini tier: {GEMINI_TIER.upper()} (delay: {RATE_LIMIT_DELAY_SECONDS}s, parallel: {ENABLE_PARALLEL})")

 
# ============================================
# HIRING DETECTION KEYWORDS
# ============================================

# Strong indicators that someone IS HIRING
HIRING_KEYWORDS = [
    # Direct hiring phrases
    "we're hiring", "we are hiring", "we're looking for", "we are looking for",
    "hiring now", "urgent hiring", "immediately hiring", "actively hiring",
    "join our team", "join us", "join the team", 
    "open position", "open positions", "open role", "open roles",
    "looking to hire", "seeking", "we need", "we require",
    "vacancy", "vacancies", "job opening", "job openings",
    "apply now", "apply today", "send your resume", "send cv",
    "interested candidates", "suitable candidates",
    "position:", "location:", "experience:", "salary:",  # Job post format
    "🚀 we're hiring", "🔎 position", "📍 location",  # Emoji job posts
    "urgent requirement", "immediate requirement", "immediate joining",
    "referral", "refer", "help us find", "know someone",
]

# Strong indicators that someone IS A JOB SEEKER (NOT hiring)
JOB_SEEKER_KEYWORDS = [
    "i am looking for", "i'm looking for", "looking for a job", "looking for job",
    "looking for opportunity", "looking for opportunities",
    "seeking job", "seeking opportunity", "seeking employment",
    "open to work", "open to opportunities", "available for",
    "currently looking", "actively looking", "actively seeking",
    "hire me", "contact me", "reach out to me",
    "dear hiring", "dear hr", "dear recruiter", "dear sir", "dear madam",
    "i am a", "i'm a", "i have experience", "my experience",
    "please consider", "kindly consider", "request you",
    "my resume", "attached resume", "find attached",
    "i can be reached", "my contact", "my email",
    "fresher", "recent graduate", "passed out",
]


def extract_json_from_response(text: str) -> dict:
    """
    Robustly extract JSON from AI response.
    Handles cases where AI wraps JSON in markdown or adds conversational text.
    """
    if not text:
        return {}
    
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
        json_str = re.sub(r',\s*([}\]])', r'\1', json_str)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            return {}

def extract_emails_from_text(text: str) -> list[str]:
    """Extract all email addresses from a string."""
    if not text:
        return []
    # Simple email regex
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    return list(set(re.findall(email_pattern, text)))

def extract_phones_from_text(text: str) -> list[str]:
    """Extract phone numbers from text (supports international formats)."""
    if not text:
        return []
    # Phone regex looking for patterns like +91..., 0... with min 10 digits
    # Matches strings that start with digit or +, followed by digits/spaces/dashes
    phone_pattern = r'\+?[\d][\d\s\-]{8,14}[\d]'
    matches = re.findall(phone_pattern, text)
    valid_phones = []
    for m in matches:
        digits_only = re.sub(r'\D', '', m)
        if 10 <= len(digits_only) <= 15:
            valid_phones.append(m.strip())
    return list(set(valid_phones))


def sanitize_for_xml(text: str) -> str:
    """
    Sanitize text for safe inclusion in XML-style prompts.
    """
    if not text:
        return ""
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    return text[:2000]


def pre_detect_hiring_intent(post_text: str) -> Tuple[str, bool, bool]:
    """
    Quick keyword-based pre-detection of hiring intent.
    This helps guide the AI and catch obvious cases.
    
    Returns:
        (hint: str, is_likely_hiring: bool, is_likely_job_seeker: bool)
    """
    text_lower = post_text.lower()
    
    hiring_score = 0
    job_seeker_score = 0
    matched_hiring = []
    matched_seeker = []
    
    for keyword in HIRING_KEYWORDS:
        if keyword in text_lower:
            hiring_score += 1
            matched_hiring.append(keyword)
    
    for keyword in JOB_SEEKER_KEYWORDS:
        if keyword in text_lower:
            job_seeker_score += 1
            matched_seeker.append(keyword)
    
    # Determine intent
    if job_seeker_score >= 2:
        return f"JOB_SEEKER (matched: {matched_seeker[:3]})", False, True
    elif hiring_score >= 2:
        return f"LIKELY_HIRING (matched: {matched_hiring[:3]})", True, False
    elif hiring_score == 1:
        return f"POTENTIAL_HIRING (matched: {matched_hiring})", True, False
    else:
        return "UNCLEAR", False, False


class LinkedInIntelligenceService:
    """
    AI service for analyzing LinkedIn posts and generating personalized DMs.
    
    Three main functions:
    1. analyze_post() - Extract hiring signals, roles, pain points (no DM)
    2. generate_dm() - Create personalized LinkedIn DM message
    3. analyze_and_generate_dm() - Combined for efficiency when both needed
    """
    
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.client = None
        self.model_name = GEMINI_MODEL_NAME
        self.last_api_call_time = 0  # For rate limiting
        
        if self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {e}")
                self.client = None
        else:
            logger.warning("GEMINI_API_KEY is missing - AI features will use fallbacks")

    def _is_available(self) -> bool:
        return self.client is not None

    async def _rate_limited_generate(self, prompt: str, use_json_mode: bool = True):
        """
        Rate-limited API call with retry logic.
        
        - Enforces minimum delay between API calls
        - Retries on 429 errors with exponential backoff
        - Returns None if all retries fail
        """
        if not self._is_available():
            return None
        
        # Enforce rate limit delay
        now = time.time()
        elapsed = now - self.last_api_call_time
        if elapsed < RATE_LIMIT_DELAY_SECONDS:
            wait_time = RATE_LIMIT_DELAY_SECONDS - elapsed
            logger.info(f"⏱️ Rate limiting: waiting {wait_time:.1f}s before next API call")
            await asyncio.sleep(wait_time)
        
        # Retry logic
        for attempt in range(MAX_RETRIES):
            try:
                self.last_api_call_time = time.time()
                
                if use_json_mode:
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
                else:
                    response = await asyncio.wait_for(
                        self.client.aio.models.generate_content(
                            model=self.model_name,
                            contents=prompt
                        ),
                        timeout=TIMEOUT_GEMINI_AI
                    )
                
                return response
                
            except Exception as e:
                error_str = str(e)
                
                # Check if it's a rate limit error
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                    retry_delay = RETRY_BASE_DELAY_SECONDS * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"⚠️ Rate limited (429). Retry {attempt + 1}/{MAX_RETRIES} in {retry_delay}s")
                    
                    if attempt < MAX_RETRIES - 1:
                        await asyncio.sleep(retry_delay)
                        continue
                    else:
                        logger.error("❌ Max retries reached for rate limit")
                        return None
                else:
                    # Other error - don't retry
                    logger.error(f"❌ API error: {e}")
                    return None
        
        return None

    async def analyze_post(
        self, 
        post_data: dict, 
        author_name: str,
        author_headline: Optional[str] = None
    ) -> dict:
        """
        Analyze a LinkedIn post for hiring signals.
        Does NOT generate DM (saves tokens when DM not needed).
        """
        if not self._is_available():
            return self._get_fallback_analysis(author_name, include_dm=False)
        
        post_text = post_data.get("text", "") or post_data.get("content", {}).get("text", "")
        hashtags = post_data.get("hashtags", [])
        posted_at = post_data.get("posted_at", {}).get("date", "recently")
        
        if not post_text:
            return self._get_fallback_analysis(author_name, include_dm=False)

        # Pre-detection hint for AI (keyword-based)
        intent_hint, is_likely_hiring, is_job_seeker = pre_detect_hiring_intent(post_text)

        # Pre-detect contact info via Regex (Highly accurate)
        regex_emails = extract_emails_from_text(post_text)
        regex_phones = extract_phones_from_text(post_text)
        
        # Sanitize for prompt
        safe_text = sanitize_for_xml(post_text)

        prompt = f"""
<context>
You are an expert at detecting hiring posts on LinkedIn.
Your goal is to identify whether the AUTHOR of this post is ACTIVELY HIRING employees and extract relevant contact/company details.
</context>

<pre_analysis>
Keyword-based pre-detection result: {intent_hint}
Regex-detected emails: {', '.join(regex_emails) if regex_emails else 'None'}
Regex-detected phones: {', '.join(regex_phones) if regex_phones else 'None'}
</pre_analysis>

<post_data>
<author_name>{sanitize_for_xml(author_name)}</author_name>
<author_headline>{sanitize_for_xml(author_headline or 'Not available')}</author_headline>
<posted_at>{sanitize_for_xml(str(posted_at))}</posted_at>
<hashtags>{sanitize_for_xml(', '.join(hashtags) if hashtags else 'None')}</hashtags>
<post_content>
{safe_text}
</post_content>
</post_data>

<detection_rules>
SET hiring_signal = TRUE if the post shows:
1. "We're Hiring", "Hiring Now", "Urgent Hiring", "Join Our Team"
2. Specific job position with location, salary, or requirements
3. "Looking for [Role]", "Need [Role]", "Open Position for [Role]"
4. Contact info (email/phone) for applying
5. Hashtags like #Hiring, #JobOpening, #WeAreHiring

SET hiring_signal = FALSE if:
1. The AUTHOR is LOOKING FOR A JOB (job seeker, not employer)
2. Someone announcing they JOINED a company (not hiring)
3. Thought leadership content about industry topics
4. Panel discussions, conferences, or events
5. Company news that doesn't include active hiring
</detection_rules>

<extraction_rules>
1. company_hiring: Extract the name of the company that is hiring. Look at the headline and post text.
2. contact_email: Extract any email mentioned for applications.
3. contact_phone: Extract any mobile/phone number mentioned for applications.
</extraction_rules>

<output_format>
{{
    "hiring_signal": true/false,
    "hiring_roles": "Role 1, Role 2" (only if hiring) or "",
    "company_hiring": "Company Name",
    "contact_email": "email@example.com",
    "contact_phone": "+1234567890",
    "pain_points": "Business challenge description",
    "key_competencies": "Skills/tools mentioned",
    "standardized_persona": "HR / TA" or "Founder" or "Recruiter" or "Operations" or "Tech" or "Sales / Marketing" or "Other",
    "detection_reasoning": "Brief explanation"
}}
</output_format>
"""

        try:
            response = await self._rate_limited_generate(prompt, use_json_mode=True)
            
            if not response:
                return self._get_fallback_analysis(author_name, include_dm=False)
            
            analysis = extract_json_from_response(response.text)
            
            if not analysis:
                return self._get_fallback_analysis(author_name, include_dm=False)
            
            # Hybrid Merge: Prefer Regex for Email/Phone if AI missed them or vice-versa
            # But regex is usually more accurate for these specific patterns
            if regex_emails and not analysis.get("contact_email"):
                analysis["contact_email"] = regex_emails[0]
            if regex_phones and not analysis.get("contact_phone"):
                analysis["contact_phone"] = regex_phones[0]
            
            # If no company name extracted by AI, try to get from headline if it looks like "Title at Company"
            if not analysis.get("company_hiring") and author_headline:
                if " at " in author_headline:
                    analysis["company_hiring"] = author_headline.split(" at ")[-1].strip()
                elif " | " in author_headline:
                    analysis["company_hiring"] = author_headline.split(" | ")[-1].strip()

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
        """
        if not self._is_available():
            return self._get_fallback_dm(author_name)
        
        post_text = sanitize_for_xml(post_data.get("text", "")[:500])
        first_name = author_name.split()[0] if author_name else "there"
        
        prompt = f"""
<context>
You are writing a LinkedIn connection request message. Keep it under 400 characters.
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
            response = await self._rate_limited_generate(prompt, use_json_mode=False)
            
            if not response:
                return self._get_fallback_dm(author_name)
            
            dm = response.text.strip().strip('"').strip("'")
            return dm[:400]
            
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
        """
        if not self._is_available():
            return self._get_fallback_analysis(author_name, include_dm=True)
        
        post_text = post_data.get("text", "") or post_data.get("content", {}).get("text", "")
        hashtags = post_data.get("hashtags", [])
        posted_at = post_data.get("posted_at", {}).get("date", "recently")
        first_name = author_name.split()[0] if author_name else "there"
        
        if not post_text:
            return self._get_fallback_analysis(author_name, include_dm=True)

        # Pre-detection hint for AI
        intent_hint, is_likely_hiring, is_job_seeker = pre_detect_hiring_intent(post_text)
        
        # Sanitize for prompt
        safe_text = sanitize_for_xml(post_text)

        prompt = f"""
<context>
You are an expert SDR analyzing a LinkedIn post and creating a personalized connection message.
</context>

<pre_analysis>
Keyword-based pre-detection: {intent_hint}
</pre_analysis>

<post_data>
<author_name>{sanitize_for_xml(author_name)}</author_name>
<author_first_name>{sanitize_for_xml(first_name)}</author_first_name>
<author_headline>{sanitize_for_xml(author_headline or 'Not available')}</author_headline>
<posted_at>{sanitize_for_xml(str(posted_at))}</posted_at>
<hashtags>{sanitize_for_xml(', '.join(hashtags) if hashtags else 'None')}</hashtags>
<post_content>
{safe_text}
</post_content>
</post_data>

<detection_rules>
HIRING SIGNAL DETECTION - Be accurate!

SET hiring_signal = TRUE when the post:
✅ Contains "We're Hiring", "Hiring Now", "Urgent Hiring", "Join Our Team"
✅ Lists a specific job position with requirements
✅ Uses format like "Position:", "Location:", "Experience:", "Salary:"
✅ Provides contact email/phone for applications
✅ Has hashtags: #Hiring, #WeAreHiring, #JobOpening, #Vacancy
✅ Says "Looking for [Role]", "Need a [Role]", "Seeking [Role]"

SET hiring_signal = FALSE when:
❌ Author is a JOB SEEKER looking for employment
   Examples: "I am looking for a job", "Dear Hiring Team", "Open to work"
❌ Someone announcing they JOINED a company
❌ Thought leadership, panel discussions, conferences
❌ Industry commentary without hiring intent
❌ Just mentioning industry (Automobile, Tech) without actual job post
</detection_rules>

<extraction_rules>
1. company_hiring: Extract the name of the company that is hiring.
2. contact_email: Extract any email mentioned for applications.
3. contact_phone: Extract any mobile/phone number mentioned for applications.
</extraction_rules>

<dm_instructions>
Write a LinkedIn connection message (max 400 chars) that:
- Uses casual professional tone
- References something SPECIFIC from their post
- Has a soft call-to-action
- Does NOT sound salesy
- Does NOT use clichés like "I hope this finds you well"
</dm_instructions>

<output_format>
Return ONLY valid JSON:
{{
    "hiring_signal": true/false,
    "hiring_roles": "Role 1, Role 2" (if hiring) or "",
    "company_hiring": "Company Name",
    "contact_email": "email@example.com",
    "contact_phone": "+1234567890",
    "pain_points": "Business challenge",
    "key_competencies": "Skills mentioned",
    "standardized_persona": "HR / TA" or "Founder" or "Recruiter" or "Operations" or "Tech" or "Other",
    "detection_reasoning": "Brief explanation",
    "linkedin_dm": "Your personalized message (max 400 chars)"
}}
</output_format>
"""

        try:
            response = await self._rate_limited_generate(prompt, use_json_mode=True)
            
            if not response:
                return self._get_fallback_analysis(author_name, include_dm=True)
            
            analysis = extract_json_from_response(response.text)
            
            if not analysis:
                return self._get_fallback_analysis(author_name, include_dm=True)
            
            # Hybrid Merge (from Regex)
            # We re-run regex here or pass it in. For simplicity, re-run on post text
            # Extract post_text same as in analyze_post
            post_text = post_data.get("text", "") or post_data.get("content", {}).get("text", "")
            if post_text:
                regex_emails = extract_emails_from_text(post_text)
                regex_phones = extract_phones_from_text(post_text)
                if regex_emails and not analysis.get("contact_email"):
                    analysis["contact_email"] = regex_emails[0]
                if regex_phones and not analysis.get("contact_phone"):
                    analysis["contact_phone"] = regex_phones[0]

            # Company name fallback
            if not analysis.get("company_hiring") and author_headline:
                if " at " in author_headline:
                    analysis["company_hiring"] = author_headline.split(" at ")[-1].strip()

            dm = analysis.get("linkedin_dm", self._get_fallback_dm(author_name))
            if len(dm) > 400:
                dm = dm[:397] + "..."
            
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

    async def batch_analyze_posts(
        self,
        leads: list[dict]
    ) -> list[dict]:
        """
        Process multiple leads with AI analysis.
        
        - On FREE tier: Sequential processing with delays
        - On PAID/ENTERPRISE tier: Parallel processing
        
        Args:
            leads: List of lead dicts with 'post_data', 'full_name', 'headline'
            
        Returns:
            List of enriched lead dicts with AI analysis added
        """
        results = []
        
        if ENABLE_PARALLEL:
            # Parallel processing for paid tiers
            logger.info(f"🚀 Parallel processing {len(leads)} leads (PAID tier)")
            
            async def analyze_one(lead):
                post_data = lead.get("post_data", [{}])[0] if lead.get("post_data") else {}
                ai_result = await self.analyze_and_generate_dm(
                    post_data=post_data,
                    author_name=lead.get("full_name", ""),
                    author_headline=lead.get("headline", "")
                )
                return {**lead, **ai_result}
            
            # Process all in parallel
            results = await asyncio.gather(
                *[analyze_one(lead) for lead in leads],
                return_exceptions=True
            )
            
            # Handle any exceptions
            final_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Lead {i} failed: {result}")
                    final_results.append({**leads[i], **self._get_fallback_analysis(leads[i].get("full_name", ""), include_dm=True)})
                else:
                    final_results.append(result)
            return final_results
            
        else:
            # Sequential processing for free tier
            logger.info(f"⏱️ Sequential processing {len(leads)} leads (FREE tier, ~{len(leads) * RATE_LIMIT_DELAY_SECONDS}s total)")
            
            for i, lead in enumerate(leads):
                logger.info(f"   Processing lead {i+1}/{len(leads)}: {lead.get('full_name', 'Unknown')}")
                
                post_data = lead.get("post_data", [{}])[0] if lead.get("post_data") else {}
                ai_result = await self.analyze_and_generate_dm(
                    post_data=post_data,
                    author_name=lead.get("full_name", ""),
                    author_headline=lead.get("headline", "")
                )
                
                results.append({**lead, **ai_result})
            
            return results


# Singleton instance for easy import
linkedin_intelligence_service = LinkedInIntelligenceService()

