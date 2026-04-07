"""
wisdom-spark-langchain — LangChain tool integration.

Usage with LangChain agents:
    from wisdom_spark.langchain import get_wisdom_tools
    tools = get_wisdom_tools(api_base="https://api.wisdomspark.ai")
    agent = create_agent(llm, tools)

Usage with LangChain chains:
    from wisdom_spark.langchain import WisdomEnricher
    enricher = WisdomEnricher()
    enriched_prompt = enricher.enrich("How should we handle immigration?")
"""

import httpx
from typing import Any


class WisdomRetriever:
    """Retrieves relevant wisdom from Wisdom Spark API."""

    def __init__(self, api_base: str = "https://api.wisdomspark.ai"):
        self.api_base = api_base.rstrip("/")
        self.client = httpx.Client(timeout=30.0)

    def get_wisdom(self, topic: str, tradition: str | None = None, limit: int = 5) -> list[dict]:
        params = {"topic": topic, "limit": limit}
        if tradition:
            params["tradition"] = tradition
        response = self.client.get(f"{self.api_base}/v1/wisdom/", params=params)
        response.raise_for_status()
        return response.json()

    def get_perspectives(self, topic: str, limit: int = 6) -> list[dict]:
        response = self.client.get(f"{self.api_base}/v1/wisdom/perspectives/{topic}", params={"limit": limit})
        response.raise_for_status()
        return response.json()

    def flourishing_score(self, text: str) -> dict:
        response = self.client.post(f"{self.api_base}/v1/wisdom/flourishing-score", json={"text": text})
        response.raise_for_status()
        return response.json()

    def close(self):
        self.client.close()


def format_wisdom_for_context(entries: list[dict]) -> str:
    """Format wisdom entries as context for injection into prompts."""
    if not entries:
        return ""

    parts = ["[Relevant Wisdom from Humanity's Philosophical Traditions]\n"]
    for entry in entries:
        trad = entry.get("tradition", {})
        trad_name = trad.get("name", "") if isinstance(trad, dict) else str(trad)
        parts.append(
            f"**{trad_name}** ({entry.get('source_author', 'Unknown')}):\n"
            f'> "{entry.get("source_text", "")[:300]}"\n'
            f"Principle: {entry.get('core_principle', '')[:200]}\n"
            f"Application: {entry.get('practical_application', '')[:200]}\n"
        )
    parts.append("[End Wisdom Context — draw on these principles where relevant]\n")
    return "\n".join(parts)


# ---- LangChain Tool Definitions ----
# These work with LangChain's @tool decorator or StructuredTool

def _get_wisdom_tool_func(api_base: str):
    """Create the get_wisdom tool function."""
    retriever = WisdomRetriever(api_base)

    def get_wisdom(query: str) -> str:
        """Search for philosophical wisdom on a topic from 17+ traditions.
        Returns curated wisdom from Stoicism, Buddhism, Vedanta, Ubuntu,
        Taoism, Confucianism, Sufism, Jainism, Indigenous wisdom, and more.
        Use this when the user asks about ethics, meaning, conflict, identity,
        or any topic that benefits from philosophical depth."""
        entries = retriever.get_wisdom(query, limit=5)
        return format_wisdom_for_context(entries)

    return get_wisdom


def _get_perspectives_tool_func(api_base: str):
    retriever = WisdomRetriever(api_base)

    def get_cross_cultural_perspectives(topic: str) -> str:
        """Get perspectives on a topic from multiple philosophical traditions.
        Shows how different cultures and philosophies approach the same question,
        revealing universal human wisdom and common ground."""
        entries = retriever.get_perspectives(topic, limit=6)
        return format_wisdom_for_context(entries)

    return get_cross_cultural_perspectives


def _get_flourishing_tool_func(api_base: str):
    retriever = WisdomRetriever(api_base)

    def check_flourishing_score(text: str) -> str:
        """Score a statement, decision, or policy against human flourishing dimensions.
        Returns scores for: reduces_suffering, respects_dignity, promotes_cooperation,
        considers_future, honors_nature. Also flags divisive content."""
        scores = retriever.flourishing_score(text)
        lines = [f"Flourishing Score for: '{text[:100]}...'"]
        for key, val in scores.items():
            if isinstance(val, (int, float)):
                lines.append(f"  {key}: {val}")
            elif isinstance(val, bool):
                lines.append(f"  {key}: {'YES' if val else 'no'}")
        return "\n".join(lines)

    return check_flourishing_score


def get_wisdom_tools(api_base: str = "https://api.wisdomspark.ai") -> list:
    """
    Get all Wisdom Spark tools ready for use with LangChain agents.

    Returns a list of callable tool functions. Compatible with:
    - LangChain's create_tool_calling_agent
    - LangChain's AgentExecutor
    - Any framework that accepts callable tools

    Usage:
        from wisdom_spark.langchain import get_wisdom_tools
        tools = get_wisdom_tools()
        # Add to your agent's tool list
    """
    return [
        _get_wisdom_tool_func(api_base),
        _get_perspectives_tool_func(api_base),
        _get_flourishing_tool_func(api_base),
    ]
