"""Crawler configuration — thresholds, schedules, and source definitions."""

from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


class CrawlerSettings(BaseSettings):
    # LLM for evaluation (Claude or OpenAI-compatible)
    llm_api_key: str = ""
    llm_api_base: str = "https://api.anthropic.com"
    llm_model: str = "claude-sonnet-4-20250514"
    llm_provider: str = "anthropic"  # "anthropic" or "openai"

    # Database
    database_url: str = "postgresql+asyncpg://localhost:5432/wisdom_spark"

    @field_validator("database_url", mode="before")
    @classmethod
    def fix_postgres_scheme(cls, v: str) -> str:
        """Render provides postgresql:// but asyncpg needs postgresql+asyncpg://."""
        if v.startswith("postgresql://"):
            v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif v.startswith("postgres://"):
            v = v.replace("postgres://", "postgresql+asyncpg://", 1)
        return v

    # Embedding
    embedding_api_key: str = ""
    embedding_api_base: str = "https://api.openai.com/v1"
    embedding_model: str = "text-embedding-3-small"

    # Crawler behavior
    crawl_interval_minutes: int = 60  # How often the main loop runs
    max_candidates_per_run: int = 50  # Max items to evaluate per cycle
    min_flourishing_score: float = 0.6  # Minimum overall score to ingest
    min_dignity_score: float = 0.7  # Hard floor — must respect dignity
    max_divisiveness: int = 0  # Zero tolerance for divisive signals
    dedup_similarity_threshold: float = 0.92  # Skip if too similar to existing

    # Rate limiting (be a good citizen)
    request_delay_seconds: float = 2.0  # Delay between HTTP requests
    max_retries: int = 3

    model_config = {"env_file": ".env", "env_prefix": "CRAWLER_"}


# Wisdom-relevant search terms organized by theme
SEARCH_QUERIES = {
    "compassion": [
        "philosophy of compassion across cultures",
        "compassion teachings world religions",
        "empathy and moral philosophy",
        "karuna metta loving kindness",
        "compassion fatigue antidote wisdom",
    ],
    "unity": [
        "philosophy of human unity",
        "overcoming racial division philosophy",
        "interfaith dialogue wisdom",
        "common ground between religions",
        "unity in diversity philosophy quotes",
        "anti-racism philosophical arguments",
        "caste abolition philosophical basis",
    ],
    "non_violence": [
        "ahimsa philosophy non-violence",
        "nonviolent resistance philosophy",
        "peace philosophy traditions",
        "conflict resolution ancient wisdom",
        "restorative justice philosophy",
    ],
    "stewardship": [
        "environmental philosophy indigenous",
        "deep ecology philosophy",
        "seven generations principle",
        "earth stewardship world religions",
        "sustainability ancient wisdom",
    ],
    "dignity": [
        "human dignity philosophy",
        "equality philosophy world traditions",
        "anti-discrimination philosophical arguments",
        "inherent worth every person philosophy",
        "ubuntu philosophy human dignity",
    ],
    "cooperation": [
        "cooperation philosophy evolutionary",
        "mutual aid philosophy",
        "community over individualism philosophy",
        "collective wellbeing philosophy",
        "common good philosophy traditions",
    ],
    "flourishing": [
        "eudaimonia human flourishing",
        "positive psychology wisdom traditions",
        "meaning of life philosophy",
        "what makes life worth living philosophy",
        "purpose and meaning across cultures",
    ],
    "forgiveness": [
        "philosophy of forgiveness",
        "reconciliation after conflict wisdom",
        "truth and reconciliation philosophy",
        "forgiveness world religions teachings",
    ],
    "self_mastery": [
        "stoic philosophy self-mastery",
        "mindfulness philosophy traditions",
        "inner peace philosophy across cultures",
        "emotional regulation ancient wisdom",
    ],
}

# Public domain and open-access sources to crawl
CURATED_SOURCES = [
    # Gutenberg texts (public domain)
    {
        "name": "Marcus Aurelius - Meditations",
        "url": "https://www.gutenberg.org/cache/epub/2680/pg2680.txt",
        "tradition": "stoicism",
        "type": "full_text",
    },
    {
        "name": "Dhammapada",
        "url": "https://www.gutenberg.org/cache/epub/2017/pg2017.txt",
        "tradition": "buddhism",
        "type": "full_text",
    },
    {
        "name": "Tao Te Ching (Lao Tzu)",
        "url": "https://www.gutenberg.org/cache/epub/216/pg216.txt",
        "tradition": "taoism",
        "type": "full_text",
    },
    {
        "name": "Analects of Confucius",
        "url": "https://www.gutenberg.org/cache/epub/4094/pg4094.txt",
        "tradition": "confucianism",
        "type": "full_text",
    },
    {
        "name": "Bhagavad Gita (Edwin Arnold translation)",
        "url": "https://www.gutenberg.org/cache/epub/2388/pg2388.txt",
        "tradition": "vedanta",
        "type": "full_text",
    },
    # Wikipedia philosophy pages (CC BY-SA)
    {
        "name": "Ubuntu Philosophy",
        "url": "https://en.wikipedia.org/api/rest_v1/page/summary/Ubuntu_philosophy",
        "tradition": "ubuntu",
        "type": "wiki_summary",
    },
    {
        "name": "Ahimsa",
        "url": "https://en.wikipedia.org/api/rest_v1/page/summary/Ahimsa",
        "tradition": "jainism",
        "type": "wiki_summary",
    },
    {
        "name": "Golden Rule",
        "url": "https://en.wikipedia.org/api/rest_v1/page/summary/Golden_Rule",
        "tradition": "universal",
        "type": "wiki_summary",
    },
]

# Anti-patterns the crawler actively seeks wisdom AGAINST
TARGET_ANTI_PATTERNS = [
    "racism", "casteism", "religious bigotry", "xenophobia",
    "dehumanization", "tribalism", "environmental destruction",
    "gender discrimination", "violence glorification", "hatred",
    "supremacism", "exploitation", "indifference to suffering",
]
