from __future__ import annotations

from app.schemas.analysis import (
    ContextAnalysis,
    ContextFactor,
    ContextOnlyResponse,
    FullAnalysisResponse,
    ImplicitStyle,
    SentenceResult,
)
from app.services.context_analyzer import ANALYSIS_FACTORS
from app.services.llm_service import LLMService
from app.services.morphology_service import MorphologyAnalyzer


class AnalyzerService:
    def __init__(self) -> None:
        self.morphology = MorphologyAnalyzer()
        self.llm = LLMService()

    # ── 1단계: 맥락 추출 ──────────────────────────────────────────────────────

    def extract_context(self, text: str) -> ContextOnlyResponse:
        raw = self.llm.extract_context(text, ANALYSIS_FACTORS)
        context_data: dict[str, str] = raw.get("context", {})
        factors = [
            ContextFactor(
                key=f["key"],
                label=f["label"],
                group=f.get("group", ""),
                value=str(context_data.get(f["key"], "")),
                description=f["description"],
            )
            for f in ANALYSIS_FACTORS
        ]

        raw_is = raw.get("implicit_style")
        implicit_style: ImplicitStyle | None = None
        if isinstance(raw_is, dict) and raw_is.get("value", "").strip():
            implicit_style = ImplicitStyle(
                value=raw_is["value"].strip(),
                reason=raw_is.get("reason", "").strip(),
            )

        context = ContextAnalysis(
            factors=factors,
            overall_summary=raw.get("overall_summary", ""),
            implicit_style=implicit_style,
        )
        return ContextOnlyResponse(context=context)

    # ── 2단계: 확정 맥락으로 문장 분석 ───────────────────────────────────────

    def analyze_sentences(
        self,
        text: str,
        context_values: dict[str, str],
        overall_summary: str,
        implicit_style_value: str = "",
    ) -> FullAnalysisResponse:
        sentence_tokens = self.morphology.analyze(text)

        # context 객체 구성 (사용자가 확정한 값)
        factors = [
            ContextFactor(
                key=f["key"],
                label=f["label"],
                group=f.get("group", ""),
                value=str(context_values.get(f["key"], "")),
                description=f["description"],
            )
            for f in ANALYSIS_FACTORS
        ]
        implicit_style: ImplicitStyle | None = None
        if implicit_style_value.strip():
            implicit_style = ImplicitStyle(value=implicit_style_value.strip(), reason="")
        context = ContextAnalysis(
            factors=factors,
            overall_summary=overall_summary,
            implicit_style=implicit_style,
        )

        # 1차: 문장별 요소 대조 + 암묵적 문체 이탈 검사
        pass1 = self.llm.check_sentences_against_context(
            text, sentence_tokens, context_values, ANALYSIS_FACTORS, implicit_style_value
        )
        sentence_map = {s.index: s.text for s in sentence_tokens}
        pass1_sentences = pass1.get("sentences", [])
        for r in pass1_sentences:
            r["text"] = sentence_map.get(r["sentence_index"], "")

        # 2차: 전체 흐름 검토
        pass2 = self.llm.check_document_flow(
            text, context_values, pass1_sentences, ANALYSIS_FACTORS
        )
        flow_by_index = {r["sentence_index"]: r for r in pass2.get("sentences", [])}
        flow_summary = pass2.get("flow_summary", "")

        # 결합
        sentences: list[SentenceResult] = []
        for r in pass1_sentences:
            idx = r["sentence_index"]
            flow = flow_by_index.get(idx, {
                "has_flow_issue": False,
                "flow_issue_reason": None,
                "flow_suggested_rewrite": None,
            })
            sentences.append(SentenceResult(
                index=idx,
                text=sentence_map.get(idx, ""),
                is_consistent=r["is_consistent"],
                violated_factors=r.get("violated_factors", []),
                inconsistency_reason=r.get("inconsistency_reason"),
                suggested_rewrite=r.get("suggested_rewrite"),
                has_flow_issue=flow.get("has_flow_issue", False),
                flow_issue_reason=flow.get("flow_issue_reason"),
                flow_suggested_rewrite=flow.get("flow_suggested_rewrite"),
                has_implicit_style_issue=r.get("has_implicit_style_issue", False),
                implicit_style_reason=r.get("implicit_style_reason"),
                implicit_style_rewrite=r.get("implicit_style_rewrite"),
            ))

        # 점수 계산
        inconsistent_count = sum(1 for s in sentences if not s.is_consistent)
        flow_issue_count = sum(1 for s in sentences if s.is_consistent and s.has_flow_issue)
        implicit_style_issue_count = sum(
            1 for s in sentences
            if s.is_consistent and not s.has_flow_issue and s.has_implicit_style_issue
        )
        total_issues = inconsistent_count + flow_issue_count + implicit_style_issue_count
        consistent_count = len(sentences) - total_issues
        overall_score = round(consistent_count / len(sentences) * 100, 1) if sentences else 0.0

        if total_issues == 0:
            summary = f"전체 {len(sentences)}개 문장이 맥락, 흐름, 문체 모두 일치합니다."
        else:
            parts = []
            if inconsistent_count:
                parts.append(f"맥락 불일치 {inconsistent_count}건")
            if flow_issue_count:
                parts.append(f"흐름 문제 {flow_issue_count}건")
            if implicit_style_issue_count:
                parts.append(f"문체 이탈 {implicit_style_issue_count}건")
            summary = f"전체 {len(sentences)}개 문장 중 {', '.join(parts)} 발견됐습니다."

        return FullAnalysisResponse(
            context=context,
            sentences=sentences,
            overall_score=overall_score,
            consistent_count=consistent_count,
            inconsistent_count=inconsistent_count,
            flow_issue_count=flow_issue_count,
            implicit_style_issue_count=implicit_style_issue_count,
            flow_summary=flow_summary,
            summary=summary,
        )
