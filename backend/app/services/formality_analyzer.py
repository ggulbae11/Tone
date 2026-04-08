from __future__ import annotations

from collections import Counter

from app.schemas.analysis import DistributionItem
from app.services.morphology_service import SentenceToken


class FormalityAnalyzer:
    formal_honorific_endings = {"습니다", "습니까", "입니다", "드립니다", "바랍니다"}
    neutral_honorific_endings = {"요"}
    informal_plain_endings = {"냐", "야", "어", "지", "다"}

    def detect_formality(self, ending: str) -> str:
        if ending in self.formal_honorific_endings:
            return "격식 존댓말"
        if ending in self.neutral_honorific_endings:
            return "중립 존댓말"
        if ending in self.informal_plain_endings:
            return "비격식 반말"
        return "중립 존댓말"

    def analyze_formality(self, sentences: list[SentenceToken]) -> dict:
        labels = [self.detect_formality(sentence.ending) for sentence in sentences]
        distribution = Counter(labels)
        dominant_label, dominant_count = distribution.most_common(1)[0] if distribution else ("mixed", 0)
        score = self.calculate_consistency_score(distribution, len(labels))

        if len(distribution) >= 3:
            dominant_label = "mixed"
        elif labels and dominant_count / len(labels) < 0.7:
            dominant_label = "mixed"

        return {
            "dominant_level": dominant_label,
            "score": score,
            "distribution": [DistributionItem(label=label, count=count) for label, count in distribution.items()],
            "sentence_labels": labels,
        }

    def calculate_consistency_score(self, distribution: Counter, sentence_count: int) -> float:
        if sentence_count == 0:
            return 0.0
        dominant_count = distribution.most_common(1)[0][1] if distribution else 0
        ratio = dominant_count / sentence_count
        return round(50 + ratio * 50, 1)