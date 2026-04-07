"""Crawl Project Gutenberg for public domain philosophical texts."""

import logging
import re
import random

import httpx

from src.crawler.config import CURATED_SOURCES
from src.crawler.sources.base import WisdomSource, RawWisdomCandidate

logger = logging.getLogger("wisdom_crawler")

# Additional Gutenberg IDs for philosophical/wisdom texts
GUTENBERG_PHILOSOPHY = [
    {"id": 2680, "title": "Meditations", "author": "Marcus Aurelius", "tradition": "stoicism"},
    {"id": 2017, "title": "Dhammapada", "author": "F. Max Muller (trans.)", "tradition": "buddhism"},
    {"id": 216, "title": "Tao Te Ching", "author": "Laozi", "tradition": "taoism"},
    {"id": 4094, "title": "Analects", "author": "Confucius", "tradition": "confucianism"},
    {"id": 2388, "title": "Bhagavad Gita", "author": "Edwin Arnold (trans.)", "tradition": "vedanta"},
    {"id": 1232, "title": "The Prince", "author": "Machiavelli", "tradition": "greek-philosophy"},
    {"id": 55201, "title": "Enchiridion", "author": "Epictetus", "tradition": "stoicism"},
    {"id": 10615, "title": "Letters from a Stoic", "author": "Seneca", "tradition": "stoicism"},
    {"id": 1497, "title": "Republic", "author": "Plato", "tradition": "greek-philosophy"},
    {"id": 8438, "title": "Nicomachean Ethics", "author": "Aristotle", "tradition": "greek-philosophy"},
    {"id": 4363, "title": "Apology", "author": "Plato", "tradition": "greek-philosophy"},
    {"id": 7370, "title": "Imitation of Christ", "author": "Thomas a Kempis", "tradition": "christian-mystics"},
    {"id": 17942, "title": "Rumi - Selected Poems", "author": "Rumi", "tradition": "sufism"},
    {"id": 2130, "title": "Utilitarianism", "author": "John Stuart Mill", "tradition": "existentialism"},
]


class GutenbergSource(WisdomSource):
    """Extract wisdom passages from Project Gutenberg public domain texts."""

    name = "gutenberg"
    delay_seconds = 3.0

    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={"User-Agent": "WisdomSparkBot/0.1 (+https://github.com/kiranz38/wisdom-spark-ai)"},
            follow_redirects=True,
        )

    async def discover(self) -> list[RawWisdomCandidate]:
        candidates = []

        # Pick a random subset each run
        sources = random.sample(GUTENBERG_PHILOSOPHY, min(3, len(GUTENBERG_PHILOSOPHY)))

        for source in sources:
            try:
                text = await self._fetch_text(source["id"])
                if not text:
                    continue

                passages = self._extract_passages(text, source)
                for passage in passages:
                    candidates.append(RawWisdomCandidate(
                        source_text=passage,
                        source_author=source["author"],
                        source_work=source["title"],
                        source_url=f"https://www.gutenberg.org/ebooks/{source['id']}",
                        tradition_hint=source["tradition"],
                        citation=f'{source["author"]}, {source["title"]} (Project Gutenberg #{source["id"]})',
                        raw_context=passage,
                        crawl_source=self.name,
                    ))

                logger.info(f"Gutenberg: {len(passages)} passages from {source['title']}")
                await self._rate_limit()

            except Exception as e:
                logger.warning(f"Gutenberg fetch failed for {source['title']}: {e}")

        logger.info(f"Gutenberg discovered {len(candidates)} candidates")
        return candidates

    async def _fetch_text(self, gutenberg_id: int) -> str | None:
        """Fetch plain text from Gutenberg."""
        url = f"https://www.gutenberg.org/cache/epub/{gutenberg_id}/pg{gutenberg_id}.txt"
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            text = response.text

            # Strip Gutenberg header/footer
            start_markers = ["*** START OF", "***START OF"]
            end_markers = ["*** END OF", "***END OF"]

            for marker in start_markers:
                idx = text.find(marker)
                if idx != -1:
                    newline = text.find("\n", idx)
                    text = text[newline + 1:]
                    break

            for marker in end_markers:
                idx = text.find(marker)
                if idx != -1:
                    text = text[:idx]
                    break

            return text.strip()
        except Exception as e:
            logger.warning(f"Failed to fetch Gutenberg #{gutenberg_id}: {e}")
            return None

    def _extract_passages(self, text: str, source: dict) -> list[str]:
        """Extract wisdom-dense paragraphs from a full text."""
        passages = []

        wisdom_keywords = [
            "virtue", "wisdom", "justice", "compassion", "soul", "truth",
            "good", "evil", "suffering", "happiness", "duty", "honor",
            "peace", "love", "nature", "reason", "mind", "spirit",
            "courage", "temperance", "mercy", "humanity", "dignity",
            "freedom", "harmony", "death", "life", "moral",
        ]

        # Split into paragraphs
        paragraphs = re.split(r'\n\s*\n', text)

        for para in paragraphs:
            para = para.strip()
            para = re.sub(r'\s+', ' ', para)

            # Skip too short or too long
            if len(para) < 80 or len(para) > 800:
                continue

            # Score by wisdom keyword density
            word_count = len(para.split())
            if word_count < 15:
                continue

            keyword_hits = sum(1 for kw in wisdom_keywords if kw.lower() in para.lower())
            density = keyword_hits / word_count

            # Require at least 2 keywords and reasonable density
            if keyword_hits >= 2 and density > 0.02:
                passages.append(para)

        # Return top passages by keyword density, shuffled for variety
        passages.sort(key=lambda p: sum(1 for kw in wisdom_keywords if kw.lower() in p.lower()), reverse=True)
        top = passages[:20]
        random.shuffle(top)
        return top[:8]

    async def close(self):
        await self.client.aclose()
