from __future__ import annotations

from app.schemas.analysis import AnalysisIssue, HighlightSpan


class ConsistencyChecker:
    def check_formality_mixing(self, sentence_texts: list[str], sentence_labels: list[str]) -> list[AnalysisIssue]:
        issues: list[AnalysisIssue] = []
        previous_label = None
        previous_text = None

        for index, (text, label) in enumerate(zip(sentence_texts, sentence_labels)):
            if previous_label and previous_label != label:
                issues.append(
                    AnalysisIssue(
                        type="formality_mixing",
                        severity="high",
                        message=f"격식 수준이 문장 사이에서 바뀌었습니다. '{previous_label}' -> '{label}'",
                        sentence_indexes=[index - 1, index],
                        highlight_texts=[previous_text or "", text],
                    )
                )
            previous_label = label
            previous_text = text

        return issues

    def build_highlights(self, issues: list[AnalysisIssue]) -> list[HighlightSpan]:
        highlights: list[HighlightSpan] = []
        for issue in issues:
            for text in issue.highlight_texts:
                if text:
                    highlights.append(HighlightSpan(text=text, type=issue.type, severity=issue.severity))
        return highlights