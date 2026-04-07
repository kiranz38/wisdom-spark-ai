"""Search the web for wisdom content using DuckDuckGo (no API key needed)."""

import asyncio
import logging
import random
import re
from urllib.parse import quote_plus

import httpx

from src.crawler.config import SEARCH_QUERIES
from src.crawler.sources.base import WisdomSource, RawWisdomCandidate

logger = logging.getLogger("wisdom_crawler")

# DuckDuckGo HTML search (no API key, lightweight)
DDG_URL = "https://html.duckduckgo.com/html/"

# Map themes to tradition hints
THEME_TRADITION_HINTS = {
    "compassion": None,
    "unity": None,
    "non_violence": "jainism",
    "stewardship": "indigenous",
    "dignity": "ubuntu",
    "cooperation": None,
    "flourishing": "greek-philosophy",
    "forgiveness": None,
    "self_mastery": "stoicism",
}


class WebSearchSource(WisdomSource):
    """Discover wisdom by searching the web for philosophical content."""

    name = "web_search"
    delay_seconds = 3.0

    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "User-Agent": "WisdomSparkBot/0.1 (https://github.com/kiranz38/wisdom-spark-ai; wisdom-crawler)"
            },
            follow_redirects=True,
        )

    async def discover(self) -> list[RawWisdomCandidate]:
        candidates = []

        # Pick random themes and queries each run (don't always search the same things)
        themes = random.sample(list(SEARCH_QUERIES.keys()), min(3, len(SEARCH_QUERIES)))

        for theme in themes:
            queries = random.sample(SEARCH_QUERIES[theme], min(2, len(SEARCH_QUERIES[theme])))
            for query in queries:
                try:
                    results = await self._search(query)
                    for result in results[:5]:
                        text = await self._extract_text(result["url"])
                        if text and len(text) > 100:
                            passages = self._extract_wisdom_passages(text)
                            for passage in passages[:3]:
                                candidates.append(RawWisdomCandidate(
                                    source_text=passage,
                                    source_url=result["url"],
                                    source_work=result.get("title", ""),
                                    tradition_hint=THEME_TRADITION_HINTS.get(theme),
                                    citation=f"Source: {result.get('title', '')} — {result['url']}",
                                    raw_context=text[:2000],
                                    crawl_source=self.name,
                                ))
                    await self._rate_limit()
                except Exception as e:
                    logger.warning(f"Search failed for '{query}': {e}")

        logger.info(f"WebSearch discovered {len(candidates)} candidates")
        return candidates

    async def _search(self, query: str) -> list[dict]:
        """Search DuckDuckGo and return result URLs + titles."""
        try:
            response = await self.client.post(
                DDG_URL,
                data={"q": query, "b": ""},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            html = response.text

            results = []
            # Extract result links from DDG HTML
            pattern = r'<a rel="nofollow" class="result__a" href="(.*?)">(.*?)</a>'
            matches = re.findall(pattern, html)
            for url, title in matches[:8]:
                # Clean HTML from title
                clean_title = re.sub(r'<.*?>', '', title).strip()
                if url.startswith("//duckduckgo.com/l/"):
                    # Extract actual URL from DDG redirect
                    actual_url_match = re.search(r'uddg=([^&]+)', url)
                    if actual_url_match:
                        from urllib.parse import unquote
                        url = unquote(actual_url_match.group(1))
                if url.startswith("http"):
                    results.append({"url": url, "title": clean_title})

            return results
        except Exception as e:
            logger.warning(f"DDG search error: {e}")
            return []

    async def _extract_text(self, url: str) -> str | None:
        """Fetch a page and extract readable text."""
        # Skip non-text resources
        skip_extensions = [".pdf", ".jpg", ".png", ".gif", ".mp4", ".zip", ".exe"]
        if any(url.lower().endswith(ext) for ext in skip_extensions):
            return None

        try:
            response = await self.client.get(url, timeout=15.0)
            response.raise_for_status()

            content_type = response.headers.get("content-type", "")
            if "text/html" not in content_type and "text/plain" not in content_type:
                return None

            text = response.text

            # Strip HTML tags (basic extraction)
            text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
            text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
            text = re.sub(r'<[^>]+>', ' ', text)
            text = re.sub(r'\s+', ' ', text).strip()

            # Only return if substantial
            if len(text) > 200:
                return text[:10000]  # Cap at 10k chars
            return None
        except Exception:
            return None

    def _extract_wisdom_passages(self, text: str) -> list[str]:
        """Extract quote-like or wisdom-dense passages from text."""
        passages = []

        # Look for quoted passages
        quote_patterns = [
            r'"([^"]{50,500})"',  # Double-quoted passages
            r'\u201c([^\u201d]{50,500})\u201d',  # Curly-quoted passages
            r'(?:said|wrote|taught|declared|observed)[:\s]+"?([^"\.]{50,400})"?',
        ]
        for pattern in quote_patterns:
            matches = re.findall(pattern, text)
            passages.extend(matches)

        # Look for sentences with wisdom keywords
        wisdom_keywords = [
            "compassion", "dignity", "justice", "peace", "wisdom",
            "humanity", "forgiveness", "unity", "harmony", "virtue",
            "conscience", "mercy", "kindness", "suffering", "liberation",
            "equality", "stewardship", "interdependence", "non-violence",
        ]
        sentences = re.split(r'(?<=[.!?])\s+', text)
        for sentence in sentences:
            sentence = sentence.strip()
            if 50 < len(sentence) < 500:
                keyword_count = sum(1 for kw in wisdom_keywords if kw.lower() in sentence.lower())
                if keyword_count >= 2:
                    passages.append(sentence)

        # Deduplicate and return
        seen = set()
        unique = []
        for p in passages:
            p_clean = p.strip()
            if p_clean not in seen and len(p_clean) > 50:
                seen.add(p_clean)
                unique.append(p_clean)
        return unique[:10]

    async def close(self):
        await self.client.aclose()
