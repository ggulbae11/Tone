from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ── 요청 ─────────────────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)


class ExtractContextRequest(BaseModel):
    """1단계: 맥락 추출만 요청"""
    text: str = Field(min_length=1, max_length=5000)


class AnalyzeSentencesRequest(BaseModel):
    """2단계: 사용자가 확인·수정한 맥락으로 문장 분석 요청"""
    text: str = Field(min_length=1, max_length=5000)
    context_values: dict[str, str]        # 사용자가 편집한 {key: value}
    overall_summary: str = ""
    implicit_style_value: str = ""        # 사용자가 확인·수정한 암묵적 문체 특성 (없으면 빈 문자열)


# ── 맥락 ─────────────────────────────────────────────────────────────────────

class ContextFactor(BaseModel):
    key: str
    label: str
    group: str = ""
    value: str
    description: str


class ImplicitStyle(BaseModel):
    """암묵적 문체 특성 — 명시적 요소로 설명되지 않는 고유한 문체 패턴"""
    value: str
    reason: str = ""   # LLM 추출 근거 (사용자 참고용, 읽기 전용)


class ContextAnalysis(BaseModel):
    factors: list[ContextFactor]
    overall_summary: str
    implicit_style: ImplicitStyle | None = None


class ContextOnlyResponse(BaseModel):
    """1단계 응답: 맥락 요소만 반환"""
    context: ContextAnalysis


# ── 문장 분석 결과 ────────────────────────────────────────────────────────────

class SentenceResult(BaseModel):
    index: int
    text: str
    # 1차: 개별 요소 대조
    is_consistent: bool
    violated_factors: list[str] = []
    inconsistency_reason: str | None = None
    suggested_rewrite: str | None = None
    # 2차: 전체 흐름 대조
    has_flow_issue: bool = False
    flow_issue_reason: str | None = None
    flow_suggested_rewrite: str | None = None
    # 3차: 암묵적 문체 이탈
    has_implicit_style_issue: bool = False
    implicit_style_reason: str | None = None
    implicit_style_rewrite: str | None = None


class FullAnalysisResponse(BaseModel):
    context: ContextAnalysis
    sentences: list[SentenceResult]
    overall_score: float
    consistent_count: int
    inconsistent_count: int
    flow_issue_count: int
    implicit_style_issue_count: int
    flow_summary: str
    summary: str


# ── 이력 ─────────────────────────────────────────────────────────────────────

class AnalysisHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    input_text: str
    overall_score: float
    formality_level: str
    tone_label: str
    issue_count: int
    result_payload: dict
    created_at: datetime


class StatsResponse(BaseModel):
    total_analyses: int
    average_score: float
    most_common_formality: str
    most_common_tone: str
