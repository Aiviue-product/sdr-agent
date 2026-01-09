import os
import asyncio
import logging
from urllib.parse import urlparse
from apify_client import ApifyClientAsync
from app.shared.core.constants import TIMEOUT_APIFY_SCRAPER, APIFY_LINKEDIN_ACTOR, MAX_SCRAPER_POSTS

logger = logging.getLogger("scraper_service")

class LinkedInScraperService:
    def __init__(self):
        self.api_token = os.getenv("APIFY_TOKEN")
        if not self.api_token:
            logger.warning("APIFY_TOKEN is missing in environment variables.") 
        self.client = ApifyClientAsync(token=self.api_token)

    def _get_username_from_url(self, url: str) -> str:
        """Extracts the username part from the URL."""
        parsed = urlparse(url)
        path_parts = [p for p in parsed.path.split("/") if p]
        if path_parts:
            return path_parts[-1]
        return "unknown"

    async def scrape_posts(self, linkedin_url: str, total_posts: int = MAX_SCRAPER_POSTS):
        """
        Scrapes a single profile's posts using Apify with timeout protection.
        """
        if not self.api_token:
            return {"error": "Scraper configuration missing"}

        username = self._get_username_from_url(linkedin_url)
        logger.info(f"Starting Scrape for: {username}")

        try:
            # Wrap the scraping logic with a timeout
            return await asyncio.wait_for(
                self._do_scrape(linkedin_url, username, total_posts),
                timeout=TIMEOUT_APIFY_SCRAPER
            )
        except asyncio.TimeoutError:
            logger.error(f"Scrape timed out for {username} (>{TIMEOUT_APIFY_SCRAPER}s)")
            return {"error": f"Scraper timed out after {TIMEOUT_APIFY_SCRAPER} seconds"}
        except Exception as e:
            logger.error(f"Scrape Failed for {username}: {e}")
            return {"error": str(e)}

    async def _do_scrape(self, linkedin_url: str, username: str, total_posts: int):
        """Internal method that performs the actual scraping."""
        # Input config for 'apimaestro/linkedin-profile-posts'
        run_input = {
            "username": linkedin_url.strip(),
            "total_posts": total_posts,
            "page_number": 1
        }

        # 1. Start the Actor
        run = await self.client.actor(APIFY_LINKEDIN_ACTOR).call(run_input=run_input)
        
        # 2. Fetch Results
        dataset_id = run["defaultDatasetId"]
        raw_posts = []
        
        # Iterate through the dataset items
        async for item in self.client.dataset(dataset_id).iterate_items():
            raw_posts.append(item)

        logger.info(f"Scrape Finished: {username} (Found {len(raw_posts)} posts)")

        # 3. Clean & Extract specific fields using your specific JSON format
        cleaned_data = self._extract_key_fields(raw_posts)
        
        return {
            "success": True,
            "profile_url": linkedin_url,
            "username": username,
            "scraped_data": cleaned_data
        }

    def _extract_key_fields(self, raw_posts: list) -> list:
        """
        Filters the raw JSON to only return relevant data for the LLM.
        Maps fields based on your Apify actor's specific output structure.
        """
        extracted = []
        
        for post in raw_posts:
            # 1. Author Info
            author = post.get("author", {})
            
            # 2. Extract Date (Handle nested 'posted_at' object)
            posted_at = post.get("posted_at", {})
            date_str = posted_at.get("date") or "Unknown Date"
            
            # 3. Extract Designation/Headline from Author block
            # In your JSON, the user's role is often in 'headline'
            designation = author.get("headline") or "Unknown Role"
            
            # 4. Post Text
            # We limit text length to save LLM tokens, but keep enough for context
            full_text = post.get("text", "") or "" 
            short_text = full_text


            # 5. Build Clean Object
            item = {
                "post_text": short_text,
                "date": date_str,
                "designation": designation,
                "post_url": post.get("url"),
                "author_name": f"{author.get('first_name', '')} {author.get('last_name', '')}".strip()
            }
            extracted.append(item)
            
        return extracted

# Singleton instance for easy import
scraper_service = LinkedInScraperService()
