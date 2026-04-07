"""Crawl Wikipedia for philosophical and wisdom-related content (CC BY-SA)."""

import logging
import random
import re

import httpx

from src.crawler.sources.base import WisdomSource, RawWisdomCandidate

logger = logging.getLogger("wisdom_crawler")

# Wikipedia articles rich in wisdom content
WIKI_ARTICLES = [
    # Philosophical concepts
    {"title": "Golden_Rule", "tradition": None},
    {"title": "Ahimsa", "tradition": "jainism"},
    {"title": "Ubuntu_philosophy", "tradition": "ubuntu"},
    {"title": "Tikkun_olam", "tradition": "jewish-wisdom"},
    {"title": "Eudaimonia", "tradition": "greek-philosophy"},
    {"title": "Ren_(Confucianism)", "tradition": "confucianism"},
    {"title": "Karuna", "tradition": "buddhism"},
    {"title": "Stoic_ethics", "tradition": "stoicism"},
    {"title": "Anekantavada", "tradition": "jainism"},
    {"title": "Four_Noble_Truths", "tradition": "buddhism"},
    {"title": "Categorical_imperative", "tradition": "existentialism"},
    {"title": "Sarbat_da_bhala", "tradition": "sikh-philosophy"},
    {"title": "Khalifah", "tradition": "islamic-ethics"},
    {"title": "Seven_generation_sustainability", "tradition": "indigenous"},
    # Thinkers
    {"title": "Marcus_Aurelius", "tradition": "stoicism"},
    {"title": "Rumi", "tradition": "sufism"},
    {"title": "Desmond_Tutu", "tradition": "ubuntu"},
    {"title": "Thich_Nhat_Hanh", "tradition": "buddhism"},
    {"title": "Viktor_Frankl", "tradition": "existentialism"},
    {"title": "Martin_Luther_King_Jr.", "tradition": "christian-mystics"},
    {"title": "Mahatma_Gandhi", "tradition": "vedanta"},
    {"title": "Nelson_Mandela", "tradition": "ubuntu"},
    {"title": "Dalai_Lama", "tradition": "buddhism"},
    {"title": "Guru_Nanak", "tradition": "sikh-philosophy"},
    {"title": "Confucius", "tradition": "confucianism"},
    {"title": "Adi_Shankara", "tradition": "vedanta"},
    {"title": "Simone_de_Beauvoir", "tradition": "existentialism"},
    {"title": "Albert_Camus", "tradition": "existentialism"},
    {"title": "Robin_Wall_Kimmerer", "tradition": "indigenous"},
    # Movements
    {"title": "Nonviolent_resistance", "tradition": None},
    {"title": "Deep_ecology", "tradition": None},
    {"title": "Interfaith_dialogue", "tradition": None},
    {"title": "Positive_psychology", "tradition": "positive-psychology"},
    {"title": "Restorative_justice", "tradition": "ubuntu"},
    {"title": "Truth_and_Reconciliation_Commission_(South_Africa)", "tradition": "ubuntu"},
]

WIKI_API = "https://en.wikipedia.org/api/rest_v1/page/summary"
WIKI_EXTRACT_API = "https://en.wikipedia.org/w/api.php"


class WikipediaSource(WisdomSource):
    """Extract wisdom-relevant content from Wikipedia articles."""

    name = "wikipedia"
    delay_seconds = 2.0

    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=20.0,
            headers={"User-Agent": "WisdomSparkBot/0.1 (https://github.com/kiranz38/wisdom-spark-ai)"},
            follow_redirects=True,
        )

    async def discover(self) -> list[RawWisdomCandidate]:
        candidates = []

        # Pick random subset each run
        articles = random.sample(WIKI_ARTICLES, min(5, len(WIKI_ARTICLES)))

        for article in articles:
            try:
                text = await self._fetch_article(article["title"])
                if not text:
                    continue

                passages = self._extract_wisdom_sentences(text)
                for passage in passages[:3]:
                    candidates.append(RawWisdomCandidate(
                        source_text=passage,
                        source_url=f"https://en.wikipedia.org/wiki/{article['title']}",
                        source_work=f"Wikipedia: {article['title'].replace('_', ' ')}",
                        tradition_hint=article.get("tradition"),
                        citation=f"Wikipedia, '{article['title'].replace('_', ' ')}' (CC BY-SA 4.0)",
                        raw_context=text[:3000],
                        crawl_source=self.name,
                    ))

                await self._rate_limit()
            except Exception as e:
                logger.warning(f"Wikipedia fetch failed for {article['title']}: {e}")

        logger.info(f"Wikipedia discovered {len(candidates)} candidates")
        return candidates

    async def _fetch_article(self, title: str) -> str | None:
        """Fetch article extract from Wikipedia API."""
        params = {
            "action": "query",
            "titles": title,
            "prop": "extracts",
            "explaintext": True,
            "exsectionformat": "plain",
            "format": "json",
        }
        try:
            response = await self.client.get(WIKI_EXTRACT_API, params=params)
            response.raise_for_status()
            data = response.json()
            pages = data.get("query", {}).get("pages", {})
            for page in pages.values():
                extract = page.get("extract", "")
                if extract:
                    return extract
            return None
        except Exception as e:
            logger.warning(f"Wiki API error for {title}: {e}")
            return None

    def _extract_wisdom_sentences(self, text: str) -> list[str]:
        """Find sentences dense in wisdom content."""
        wisdom_signals = [
            "compassion", "dignity", "justice", "equality", "peace",
            "non-violence", "nonviolence", "forgiveness", "mercy",
            "wisdom", "virtue", "harmony", "unity", "humanity",
            "suffering", "liberation", "stewardship", "moral",
            "ethical", "conscience", "empathy", "kindness",
            "taught", "believed", "philosophy", "principle",
        ]

        sentences = re.split(r'(?<=[.!?])\s+', text)
        scored = []

        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 60 or len(sentence) > 500:
                continue

            hits = sum(1 for kw in wisdom_signals if kw.lower() in sentence.lower())
            if hits >= 2:
                scored.append((hits, sentence))

        scored.sort(reverse=True)
        return [s for _, s in scored[:10]]

    async def close(self):
        await self.client.aclose()
