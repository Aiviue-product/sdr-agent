"""
LinkedIn Search Service
Searches LinkedIn posts by keywords using Apify actor.
Parses author data and prepares leads for repository.
"""
import os
import re
import asyncio
import logging
from typing import List, Optional
from urllib.parse import urlparse, urlunparse
from apify_client import ApifyClientAsync
from app.shared.core.constants import (
    APIFY_LINKEDIN_SEARCH_ACTOR, 
    TIMEOUT_APIFY_LINKEDIN_SEARCH
)

logger = logging.getLogger("linkedin_search_service")


# ============================================
# COMPANY DETECTION PATTERNS
# ============================================
COMPANY_KEYWORDS = [
    "jobs", "careers", "hiring", "recruitment", "staffing",
    "inc", "inc.", "llc", "ltd", "ltd.", "limited", "corp", "corporation",
    "group", "solutions", "services", "consulting", "agency",
    "technologies", "tech", "software", "systems"
]


class LinkedInSearchService:
    """
    Service to search LinkedIn posts by keywords and extract lead data.
    Uses Apify actor: apimaestro/linkedin-posts-search-scraper-no-cookies
    """
    
    def __init__(self):
        self.api_token = os.getenv("APIFY_TOKEN")
        if not self.api_token:
            logger.warning("APIFY_TOKEN is missing in environment variables.")
        self.client = ApifyClientAsync(token=self.api_token)
        self.actor_id = APIFY_LINKEDIN_SEARCH_ACTOR

    async def search_by_keywords(
        self,
        keywords: List[str],
        date_filter: str = "past-week",
        posts_per_keyword: int = 10,
        page_number: int = 1
    ) -> dict:
        """
        Search LinkedIn posts by keywords.
        
        Args:
            keywords: List of search terms (e.g., ["hiring software engineer", "looking for developer"])
            date_filter: One of 'past-24h', 'past-week', 'past-month'
            posts_per_keyword: Number of posts to fetch per keyword
            page_number: Page number for pagination
            
        Returns:
            dict with:
                - success: bool
                - raw_posts: List of raw Apify responses
                - leads: List of parsed lead data ready for repository
                - stats: {total_posts, unique_leads, keywords_searched}
        """
        if not self.api_token:
            return {"success": False, "error": "APIFY_TOKEN not configured"}

        all_raw_posts = []
        
        logger.info(f"🔍 Searching LinkedIn for {len(keywords)} keywords...")

        for keyword in keywords:
            try:
                posts = await self._search_single_keyword(
                    keyword=keyword,
                    date_filter=date_filter,
                    limit=posts_per_keyword,
                    page_number=page_number
                )
                all_raw_posts.extend(posts)
                logger.info(f"   ✅ '{keyword}' → {len(posts)} posts found")
                
            except asyncio.TimeoutError:
                logger.error(f"   ⏱️ Timeout for '{keyword}'")
            except Exception as e:
                logger.error(f"   ❌ Error for '{keyword}': {e}")

        # Parse raw posts into lead format
        leads = self._parse_posts_to_leads(all_raw_posts)
        
        # Deduplicate by linkedin_url (same person might appear in multiple posts)
        unique_leads = self._deduplicate_leads(leads)

        return {
            "success": True,
            "raw_posts": all_raw_posts,
            "leads": unique_leads,
            "stats": {
                "total_posts": len(all_raw_posts),
                "unique_leads": len(unique_leads),
                "keywords_searched": len(keywords)
            }
        }

    async def _search_single_keyword(
        self,
        keyword: str,
        date_filter: str,
        limit: int,
        page_number: int
    ) -> List[dict]:
        """
        Search posts for a single keyword with timeout protection.
        """
        run_input = {
            "keyword": keyword,
            "date_filter": date_filter,
            "limit": limit,
            "page_number": page_number,
            "sort_type": "date_posted"
        }

        # Run actor with timeout
        run = await asyncio.wait_for(
            self.client.actor(self.actor_id).call(run_input=run_input),
            timeout=TIMEOUT_APIFY_LINKEDIN_SEARCH
        )

        # Fetch results
        dataset_id = run["defaultDatasetId"]
        posts = []
        
        async for item in self.client.dataset(dataset_id).iterate_items():
            posts.append(item)

        return posts

    def _parse_posts_to_leads(self, raw_posts: List[dict]) -> List[dict]:
        """
        Transform raw Apify posts into lead format for repository.
        
        Extracts author info and prepares data structure.
        """
        leads = []
        
        for post in raw_posts:
            author = post.get("author", {})
            
            # Skip posts without author info
            if not author or not author.get("profile_url"):
                continue
            
            # Parse author name
            name_info = self._parse_author_name(author.get("name", ""))
            
            # Normalize LinkedIn URL (remove query params)
            linkedin_url = self._normalize_linkedin_url(author.get("profile_url", ""))
            
            # Get search keyword (Apify returns as 'search_input')
            search_keyword = post.get("search_input", "")
            
            lead = {
                # Identity
                "full_name": name_info["full_name"],
                "first_name": name_info["first_name"],
                "last_name": name_info["last_name"],
                "company_name": name_info["company_name"],
                "is_company": name_info["is_company"],
                
                # LinkedIn info
                "linkedin_url": linkedin_url,
                "headline": author.get("headline", ""),
                "profile_image_url": author.get("image_url", ""),
                
                # Search context
                "search_keyword": search_keyword,
                "post_data": post,  # Store full post for reference
                
                # AI fields (will be filled later)
                "hiring_signal": False,
                "hiring_roles": None,
                "pain_points": None,
                "ai_variables": {},
                "linkedin_dm": None
            }
            
            leads.append(lead)
        
        return leads

    def _parse_author_name(self, name: str) -> dict:
        """
        Parse author name into components.
        Detects company pages vs person profiles.
        
        Examples:
            "Rajwinder Pal" → {full_name: "Rajwinder Pal", first_name: "Rajwinder", 
                               last_name: "Pal", is_company: False, company_name: None}
            
            "Tucson Jobs, Arizona" → {full_name: "Tucson Jobs, Arizona", first_name: None,
                                       last_name: None, is_company: True, 
                                       company_name: "Tucson Jobs, Arizona"}
        """
        if not name:
            return {
                "full_name": "Unknown",
                "first_name": None,
                "last_name": None,
                "is_company": False,
                "company_name": None
            }
        
        name = name.strip()
        
        # Detect company page
        is_company = self._is_company_page(name)
        
        if is_company:
            return {
                "full_name": name,
                "first_name": None,
                "last_name": None,
                "is_company": True,
                "company_name": name
            }
        else:
            # Split name for person
            parts = name.split(" ", 1)  # Split on first space only
            first_name = parts[0] if parts else None
            last_name = parts[1] if len(parts) > 1 else None
            
            return {
                "full_name": name,
                "first_name": first_name,
                "last_name": last_name,
                "is_company": False,
                "company_name": None
            }

    def _is_company_page(self, name: str) -> bool:
        """
        Detect if the name looks like a company page rather than a person.
        
        Signals:
        - Contains comma (e.g., "Tucson Jobs, Arizona")
        - Contains company keywords (Jobs, Inc, LLC, etc.)
        - URL pattern suggests showcase/company page
        """
        name_lower = name.lower()
        
        # Check for comma (common in location-based company names)
        if "," in name:
            return True
        
        # Check for company keywords
        for keyword in COMPANY_KEYWORDS:
            # Match as whole word (avoid matching "technologies" in person names)
            if re.search(rf'\b{keyword}\b', name_lower):
                return True
        
        return False

    def _normalize_linkedin_url(self, url: str) -> str:
        """
        Normalize LinkedIn URL by removing query parameters.
        
        Example:
            Input:  https://linkedin.com/in/rajwinder-pal?miniProfileUrn=...
            Output: https://linkedin.com/in/rajwinder-pal
        """
        if not url:
            return ""
        
        try:
            parsed = urlparse(url)
            # Reconstruct URL without query params
            normalized = urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path.rstrip('/'),  # Remove trailing slash
                '',  # params
                '',  # query (removed!)
                ''   # fragment
            ))
            return normalized
        except Exception:
            return url

    def _deduplicate_leads(self, leads: List[dict]) -> List[dict]:
        """
        Remove duplicate leads by linkedin_url.
        Keeps the first occurrence of each lead.
        
        Note: The repository handles true dedup against DB,
        this is just for within-batch dedup.
        """
        seen_urls = set()
        unique = []
        
        for lead in leads:
            url = lead.get("linkedin_url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique.append(lead)
        
        return unique


# Singleton instance for easy import
linkedin_search_service = LinkedInSearchService()
