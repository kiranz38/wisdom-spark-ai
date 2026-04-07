"""Base class for all wisdom sources."""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

logger = logging.getLogger("wisdom_crawler")


@dataclass
class RawWisdomCandidate:
    """A piece of content discovered by a source, not yet evaluated."""
    source_text: str
    source_author: str | None = None
    source_work: str | None = None
    source_url: str | None = None
    source_era: str | None = None
    original_language: str | None = None
    tradition_hint: str | None = None  # Best guess at tradition slug
    citation: str | None = None
    raw_context: str | None = None  # Surrounding text for LLM evaluation
    crawl_source: str = ""  # Which source class found this


class WisdomSource(ABC):
    """Base class for all wisdom content sources."""

    name: str = "base"
    delay_seconds: float = 2.0

    @abstractmethod
    async def discover(self) -> list[RawWisdomCandidate]:
        """Discover new wisdom candidates from this source."""
        ...

    async def _rate_limit(self):
        await asyncio.sleep(self.delay_seconds)
