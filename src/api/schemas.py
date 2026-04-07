"""Pydantic schemas for API request/response."""

from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field


# ---- Traditions ----

class TraditionOut(BaseModel):
    id: UUID
    slug: str
    name: str
    origin_region: str | None
    era: str | None
    description: str
    key_figures: list[str] | None
    core_principles: list[str] | None

    model_config = {"from_attributes": True}


# ---- Themes ----

class ThemeOut(BaseModel):
    id: UUID
    slug: str
    name: str
    description: str
    anti_patterns: list[str] | None

    model_config = {"from_attributes": True}


# ---- Wisdom Entries ----

class WisdomEntryOut(BaseModel):
    id: UUID
    source_text: str
    source_author: str | None
    source_work: str | None
    source_era: str | None
    original_language: str | None
    core_principle: str
    practical_application: str
    modern_context: str | None
    addresses_anti_patterns: list[str] | None
    reduces_suffering: float
    respects_dignity: float
    promotes_cooperation: float
    considers_future: float
    honors_nature: float
    verified: bool
    citation: str | None
    tradition: TraditionOut | None
    themes: list[ThemeOut]
    created_at: datetime

    model_config = {"from_attributes": True}


class WisdomQuery(BaseModel):
    topic: str | None = None
    tradition: str | None = None
    theme: str | None = None
    limit: int = Field(default=10, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class SemanticSearchQuery(BaseModel):
    query: str = Field(..., min_length=3, max_length=2000)
    limit: int = Field(default=10, ge=1, le=50)


# ---- Flourishing Score ----

class FlourishingScoreRequest(BaseModel):
    text: str = Field(..., min_length=10, max_length=10000)


class FlourishingScoreResponse(BaseModel):
    reduces_suffering: float
    respects_dignity: float
    promotes_cooperation: float
    considers_future: float
    honors_nature: float
    overall: float
    divisiveness_flag: bool
    negative_signal_count: int


# ---- Reframe ----

class ReframeRequest(BaseModel):
    text: str = Field(..., min_length=10, max_length=5000)


class ReframeResponse(BaseModel):
    original_text: str
    divisiveness_flag: bool
    wisdom_perspectives: list[WisdomEntryOut]
    reframing_guidance: str


# ---- Cross References ----

class CrossReferenceOut(BaseModel):
    id: UUID
    source_id: UUID
    target_id: UUID
    relationship_type: str
    explanation: str
    similarity_score: float

    model_config = {"from_attributes": True}
