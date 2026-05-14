"""Structured AI coaching analysis schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.enriched_match import EnrichedMatchContext, SourceWarning
from app.schemas.retrieval import RetrievalContext

SCHEMA_VERSION = "coaching-analysis-v1"
PROMPT_VERSION = "coaching-analysis-prompt-v1"
WORKFLOW_VERSION = "structured-ai-analysis-v1"

CoachingCategory = Literal[
    "laning",
    "fighting",
    "objectives",
    "economy",
    "positioning",
    "build",
    "macro",
    "other",
]
ImpactLevel = Literal["low", "medium", "high"]
ConfidenceLevel = Literal["low", "medium", "high"]
EvidenceSourceType = Literal["user_summary", "replay_parse", "deadlock_api", "strategy_knowledge", "ai_inference"]


class AnalysisInputContext(BaseModel):
    """Compact model input context assembled from app-owned sources."""

    upload_kind: str
    match_summary_text: str | None = None
    replay_parse_summary: dict[str, Any] | None = None
    enriched_context: EnrichedMatchContext | None = None
    retrieval_context: RetrievalContext | None = None
    source_warnings: list[str] = Field(default_factory=list)


class MatchContextSummary(BaseModel):
    """Human-readable match context summarized by the model."""

    hero: str | None = None
    match_id: int | None = None
    source_mode: str
    duration_seconds: int | None = None
    summary: str


class CoachingPoint(BaseModel):
    """One strength or improvement area."""

    title: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=1000)
    impact: ImpactLevel
    category: CoachingCategory
    evidence_refs: list[str] = Field(default_factory=list)


class KeyMoment(BaseModel):
    """A timestamped or contextual moment from the match."""

    title: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=1000)
    timestamp_seconds: int | None = None
    impact: ImpactLevel = "medium"
    evidence_refs: list[str] = Field(default_factory=list)


class BuildAdvice(BaseModel):
    """Item/build coaching derived from available context."""

    title: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=1000)
    item_name: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)


class PracticeFocus(BaseModel):
    """A concrete next practice item for the user."""

    title: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=1000)
    timebox_minutes: int | None = Field(default=None, ge=1, le=240)
    evidence_refs: list[str] = Field(default_factory=list)


class SourceEvidence(BaseModel):
    """Citation-like source reference used by coaching sections."""

    ref_id: str = Field(min_length=1, max_length=80)
    source_type: EvidenceSourceType
    description: str = Field(min_length=1, max_length=1000)
    data_path: str | None = None


class ModelMetadata(BaseModel):
    """Safe model metadata returned with the result."""

    provider: str
    model: str
    prompt_version: str = PROMPT_VERSION
    workflow_version: str = WORKFLOW_VERSION


class CoachingAnalysisResult(BaseModel):
    """Versioned structured result persisted in AnalysisResult.payload."""

    schema_version: Literal["coaching-analysis-v1"] = SCHEMA_VERSION
    title: str = Field(min_length=1, max_length=255)
    executive_summary: str = Field(min_length=1, max_length=2000)
    confidence: ConfidenceLevel
    match_context: MatchContextSummary
    strengths: list[CoachingPoint] = Field(default_factory=list)
    improvement_areas: list[CoachingPoint] = Field(default_factory=list)
    key_moments: list[KeyMoment] = Field(default_factory=list)
    build_advice: list[BuildAdvice] = Field(default_factory=list)
    priority_focus: list[PracticeFocus] = Field(default_factory=list)
    evidence: list[SourceEvidence] = Field(default_factory=list)
    source_warnings: list[SourceWarning] = Field(default_factory=list)
    model_metadata: ModelMetadata

    @property
    def summary(self) -> str:
        """AnalysisResult.summary-compatible short text."""
        return self.executive_summary[:1000]
