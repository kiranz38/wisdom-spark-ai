"""Service for generating text embeddings via OpenAI-compatible API."""

from openai import AsyncOpenAI
from src.config import get_settings

settings = get_settings()

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=settings.embedding_api_key,
            base_url=settings.embedding_api_base,
        )
    return _client


async def get_embedding(text: str) -> list[float]:
    """Generate an embedding vector for the given text."""
    client = _get_client()
    response = await client.embeddings.create(
        model=settings.embedding_model,
        input=text,
        dimensions=settings.embedding_dimensions,
    )
    return response.data[0].embedding


async def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a batch of texts."""
    client = _get_client()
    response = await client.embeddings.create(
        model=settings.embedding_model,
        input=texts,
        dimensions=settings.embedding_dimensions,
    )
    return [item.embedding for item in sorted(response.data, key=lambda x: x.index)]
