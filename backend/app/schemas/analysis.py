from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


FormalityLevel = Literal["격식 존댓말", "중립 존댓말", "비격식 반말", "mixed"]
ToneLabel = Literal["respectful", "neutral", "requesting", "directive", "friendly"]
SeverityLabel = Literal["high", "medium", "low"]
RewriteSource = Literal["ai", "rule-based"]
TargetRewriteLevel = Literal["격식 존댓말", "중립 존댓말", "비격식 반말"]


class AnalyzeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)


class RewritePlanRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    target_level: TargetRewriteLevel


class SentenceAnalysis(BaseModel):
    index: int
    text: str
    ending: str
    formality: FormalityLevel


class DistributionItem(BaseModel):
    label: str
    count: int


class AnalysisIssue(BaseModel):
    type: str
    severity: SeverityLabel
    message: str
    sentence_indexes: list[int] = Field(default_factory=list)
    highlight_texts: list[str] = Field(default_factory=list)


class HighlightSpan(BaseModel):
    text: str
    type: str
    severity: SeverityLabel


class RewriteSuggestion(BaseModel):
    sentence_index: int
    original_sentence: str
    current_formality: str
    target_formality: str
    reason: str
    suggested_sentence: str
    source: RewriteSource


class RewritePlanResponse(BaseModel):
    target_level: TargetRewriteLevel
    dominant_formality: FormalityLevel
    available_levels: list[str]
    summary: str
    rewrites: list[RewriteSuggestion]


class FullAnalysisResponse(BaseModel):
    overall_score: float
    formality_level: FormalityLevel
    formality_score: float
    consistency_score: float
    tone_label: ToneLabel
    tone_confidence: float
    sentence_count: int
    endings_distribution: list[DistributionItem]
    sentences: list[SentenceAnalysis]
    issues: list[AnalysisIssue]
    highlights: list[HighlightSpan]
    summary: str


class AnalysisHistoryItem(BaseModel):
    id: int
    input_text: str
    overall_score: float
    formality_level: str
    tone_label: str
    issue_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class StatsResponse(BaseModel):
    total_analyses: int
    average_score: float
    most_common_formality: str
    most_common_tone: str