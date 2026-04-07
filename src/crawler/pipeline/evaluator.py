"""
LLM-powered Wisdom Evaluator

Takes raw discovered content and uses an LLM to:
1. Determine if it qualifies as genuine wisdom
2. Extract the core principle
3. Generate practical application
4. Score against flourishing dimensions
5. Map to traditions and themes
6. Flag any divisive or harmful content

This is the gatekeeper — only wisdom that passes evaluation enters the database.
"""

import json
import logging
from dataclasses import dataclass

import httpx

from src.crawler.config import CrawlerSettings
from src.crawler.sources.base import RawWisdomCandidate

logger = logging.getLogger("wisdom_crawler")

EVALUATION_PROMPT = """You are the Wisdom Evaluator for Wisdom Spark AI — a project that curates humanity's deepest philosophical wisdom to feed AI models.

You are given a raw text passage discovered by a web crawler. Your job is to determine if this qualifies as genuine, high-quality wisdom that promotes human flourishing, cooperation, and the reduction of suffering.

EVALUATE this passage:

---
Source Text: {source_text}
Source Author: {source_author}
Source Work: {source_work}
Source URL: {source_url}
Tradition Hint: {tradition_hint}
---

Respond with a JSON object (no markdown, no explanation, just valid JSON):

{{
  "qualifies": true/false,
  "rejection_reason": "string or null — why it was rejected if qualifies=false",
  "divisiveness_detected": true/false,
  "core_principle": "The extracted wisdom principle (1-3 sentences)",
  "practical_application": "How to apply this in modern life (2-4 sentences)",
  "modern_context": "Why this matters today (1-3 sentences)",
  "source_author": "Best attribution (clean up if needed)",
  "source_era": "Time period (e.g., '5th century BCE', '13th century CE')",
  "original_language": "Original language if known, else null",
  "tradition_slug": "One of: stoicism, buddhism, vedanta, ubuntu, taoism, confucianism, sufism, jainism, indigenous, existentialism, positive-psychology, islamic-ethics, jewish-wisdom, sikh-philosophy, greek-philosophy, african-proverbs, christian-mystics, or 'other'",
  "themes": ["array of theme slugs from: compassion, non-harm, dignity, stewardship, cooperation, golden-rule, self-mastery"],
  "addresses_anti_patterns": ["array of problems this wisdom addresses, e.g., 'racism', 'tribalism', 'environmental destruction'"],
  "flourishing_scores": {{
    "reduces_suffering": 0.0-1.0,
    "respects_dignity": 0.0-1.0,
    "promotes_cooperation": 0.0-1.0,
    "considers_future": 0.0-1.0,
    "honors_nature": 0.0-1.0
  }}
}}

QUALIFICATION CRITERIA:
- MUST promote human flourishing, cooperation, compassion, dignity, or ecological stewardship
- MUST be genuinely wise — not just popular, motivational, or platitudinous
- MUST NOT contain divisive, supremacist, or dehumanizing content
- MUST be attributable (not anonymous clickbait)
- SHOULD offer practical value — not just abstract theory
- SHOULD address one or more anti-patterns (racism, tribalism, environmental destruction, etc.)
- PREFER cross-cultural relevance — wisdom that resonates beyond its tradition of origin

If the passage is NOT genuine wisdom (trivial, harmful, divisive, commercial, or just motivational fluff), set qualifies=false and explain why.

Return ONLY the JSON object."""


@dataclass
class EvaluatedWisdom:
    """A wisdom candidate that has been evaluated and approved by the LLM."""
    qualifies: bool
    rejection_reason: str | None
    source_text: str
    source_author: str | None
    source_work: str | None
    source_url: str | None
    source_era: str | None
    original_language: str | None
    core_principle: str
    practical_application: str
    modern_context: str | None
    tradition_slug: str
    themes: list[str]
    addresses_anti_patterns: list[str]
    flourishing_scores: dict
    divisiveness_detected: bool
    citation: str | None
    crawl_source: str


class WisdomEvaluator:
    """Uses LLM to evaluate raw candidates and produce structured wisdom entries."""

    def __init__(self, settings: CrawlerSettings | None = None):
        self.settings = settings or CrawlerSettings()
        self.client = httpx.AsyncClient(timeout=60.0)

    async def evaluate(self, candidate: RawWisdomCandidate) -> EvaluatedWisdom | None:
        """Evaluate a single candidate. Returns EvaluatedWisdom if it qualifies, None if rejected."""
        try:
            prompt = EVALUATION_PROMPT.format(
                source_text=candidate.source_text[:2000],
                source_author=candidate.source_author or "Unknown",
                source_work=candidate.source_work or "Unknown",
                source_url=candidate.source_url or "None",
                tradition_hint=candidate.tradition_hint or "Unknown",
            )

            result = await self._call_llm(prompt)
            if not result:
                return None

            # Parse LLM response
            data = self._parse_response(result)
            if not data:
                return None

            # Hard rejection criteria
            if data.get("divisiveness_detected"):
                logger.info(f"Rejected (divisive): {candidate.source_text[:80]}...")
                return None

            if not data.get("qualifies"):
                reason = data.get("rejection_reason", "Unknown")
                logger.info(f"Rejected ({reason}): {candidate.source_text[:80]}...")
                return None

            # Check flourishing scores against thresholds
            scores = data.get("flourishing_scores", {})
            overall = sum(scores.values()) / max(len(scores), 1)
            if overall < self.settings.min_flourishing_score:
                logger.info(f"Rejected (low flourishing {overall:.2f}): {candidate.source_text[:80]}...")
                return None

            if scores.get("respects_dignity", 0) < self.settings.min_dignity_score:
                logger.info(f"Rejected (low dignity {scores.get('respects_dignity', 0):.2f}): {candidate.source_text[:80]}...")
                return None

            return EvaluatedWisdom(
                qualifies=True,
                rejection_reason=None,
                source_text=candidate.source_text.strip(),
                source_author=data.get("source_author") or candidate.source_author,
                source_work=candidate.source_work,
                source_url=candidate.source_url,
                source_era=data.get("source_era"),
                original_language=data.get("original_language"),
                core_principle=data["core_principle"],
                practical_application=data["practical_application"],
                modern_context=data.get("modern_context"),
                tradition_slug=data.get("tradition_slug", "other"),
                themes=data.get("themes", []),
                addresses_anti_patterns=data.get("addresses_anti_patterns", []),
                flourishing_scores=scores,
                divisiveness_detected=False,
                citation=candidate.citation,
                crawl_source=candidate.crawl_source,
            )

        except Exception as e:
            logger.error(f"Evaluation failed: {e}")
            return None

    async def evaluate_batch(self, candidates: list[RawWisdomCandidate]) -> list[EvaluatedWisdom]:
        """Evaluate a batch of candidates sequentially (to respect rate limits)."""
        approved = []
        for candidate in candidates:
            result = await self.evaluate(candidate)
            if result:
                approved.append(result)
        logger.info(f"Evaluated {len(candidates)} candidates, approved {len(approved)}")
        return approved

    async def _call_llm(self, prompt: str) -> str | None:
        """Call the LLM for evaluation."""
        try:
            if self.settings.llm_provider == "anthropic":
                return await self._call_anthropic(prompt)
            else:
                return await self._call_openai(prompt)
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return None

    async def _call_anthropic(self, prompt: str) -> str | None:
        response = await self.client.post(
            f"{self.settings.llm_api_base}/v1/messages",
            headers={
                "x-api-key": self.settings.llm_api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": self.settings.llm_model,
                "max_tokens": 1500,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["content"][0]["text"]

    async def _call_openai(self, prompt: str) -> str | None:
        response = await self.client.post(
            f"{self.settings.llm_api_base}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.settings.llm_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.settings.llm_model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 1500,
                "temperature": 0.3,
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    def _parse_response(self, text: str) -> dict | None:
        """Parse LLM JSON response, handling common formatting issues."""
        text = text.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            text = text.split("\n", 1)[-1]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to find JSON object in the response
            start = text.find("{")
            end = text.rfind("}") + 1
            if start != -1 and end > start:
                try:
                    return json.loads(text[start:end])
                except json.JSONDecodeError:
                    pass
            logger.warning(f"Failed to parse LLM response: {text[:200]}")
            return None

    async def close(self):
        await self.client.aclose()
