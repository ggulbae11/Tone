from __future__ import annotations

from statistics import mean

from app.schemas.analysis import FullAnalysisResponse, RewritePlanResponse, RewriteSuggestion, SentenceAnalysis
from app.services.consistency_checker import ConsistencyChecker
from app.services.llm_service import LLMService
from app.services.morphology_service import MorphologyAnalyzer
from app.services.tone_analyzer import ToneAnalyzer


class AnalyzerService:
    def __init__(self) -> None:
        self.morphology = MorphologyAnalyzer()
        self.consistency = ConsistencyChecker()
        self.tone = ToneAnalyzer()
        self.llm = LLMService()

    def analyze_full(self, text: str) -> FullAnalysisResponse:
        sentence_tokens = self.morphology.analyze(text)
        formality_result = self.llm.classify_formality(sentence_tokens)
        tone_result = self.tone.analyze(text)

        sentence_texts = [sentence.text for sentence in sentence_tokens]
        issues = self.consistency.check_formality_mixing(sentence_texts, formality_result["sentence_labels"])
        highlights = self.consistency.build_highlights(issues)

        issue_penalty = min(len(issues) * 8, 40)
        confidence_values = formality_result.get("sentence_confidences", [])
        average_confidence = sum(confidence_values) / len(confidence_values) if confidence_values else 0.0
        formality_score = round((formality_result["score"] * 0.75) + (average_confidence * 25), 1)

        overall_score = max(
            0.0,
            round(
                mean(
                    [
                        formality_score,
                        100 - issue_penalty,
                        tone_result["confidence"] * 100,
                    ]
                ),
                1,
            ),
        )

        sentences = [
            SentenceAnalysis(
                index=sentence.index,
                text=sentence.text,
                ending=sentence.ending,
                formality=formality_result["sentence_labels"][sentence.index],
            )
            for sentence in sentence_tokens
        ]

        summary = self._build_summary(
            formality_result["dominant_level"],
            tone_result["label"],
            len(issues),
            formality_result.get("source", "ai"),
        )

        return FullAnalysisResponse(
            overall_score=overall_score,
            formality_level=formality_result["dominant_level"],
            formality_score=formality_score,
            consistency_score=max(0.0, round(100 - issue_penalty, 1)),
            tone_label=tone_result["label"],
            tone_confidence=round(tone_result["confidence"], 2),
            sentence_count=len(sentences),
            endings_distribution=formality_result["distribution"],
            sentences=sentences,
            issues=issues,
            highlights=highlights,
            summary=summary,
        )

    def create_rewrite_plan(self, text: str, target_level: str) -> RewritePlanResponse:
        analysis = self.analyze_full(text)
        available_levels = [item.label for item in analysis.endings_distribution if item.label != "mixed"]
        mismatched_sentences = [sentence for sentence in analysis.sentences if sentence.formality != target_level]

        if not mismatched_sentences:
            return RewritePlanResponse(
                target_level=target_level,
                dominant_formality=analysis.formality_level,
                available_levels=available_levels,
                summary=f"현재 문서는 '{target_level}' 격식으로 이미 정렬되어 있습니다.",
                rewrites=[],
            )

        rewrites = self.llm.suggest_rewrites(
            original_text=text,
            target_level=target_level,
            sentences=mismatched_sentences,
        )

        validated = [RewriteSuggestion(**item) for item in rewrites]
        summary = f"선택한 격식 '{target_level}'에 맞추기 위해 {len(validated)}개 문장을 제안했습니다."

        return RewritePlanResponse(
            target_level=target_level,
            dominant_formality=analysis.formality_level,
            available_levels=available_levels,
            summary=summary,
            rewrites=validated,
        )

    def _build_summary(self, formality_level: str, tone_label: str, issue_count: int, source: str) -> str:
        source_note = "AI 기반" if source == "ai" else "규칙 기반 보완"
        if issue_count == 0:
            return f"{source_note} 분석 기준으로 문서는 전반적으로 '{formality_level}' 격식을 유지하고 있으며 톤은 '{tone_label}'에 가깝습니다."
        return f"{source_note} 분석 기준으로 문서에서 '{formality_level}' 격식이 관찰되지만, 일관성 관련 이슈가 {issue_count}건 있습니다."