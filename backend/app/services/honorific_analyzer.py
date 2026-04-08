from __future__ import annotations

from collections import Counter

from app.schemas.analysis import DistributionItem
from app.services.morphology_service import SentenceToken


class HonorificAnalyzer:
    honorific_markers = ["께서", "께", "님", "드리", "모시", "말씀", "여쭙", "주시"]
    plain_markers = ["너", "야", "해줘", "보내줘", "왔어", "했어", "봐줘"]
    honorific_endings = {"습니다", "습니까", "입니다", "요", "어요", "아요", "예요", "이에요", "해주세요", "주세요"}

    def detect_honorific(self, sentence: SentenceToken) -> str:
        text = sentence.text
        if any(marker in text for marker in self.plain_markers):
            return "plain"
        if any(marker in text for marker in self.honorific_markers):
            return "honorific"
        if sentence.ending in self.honorific_endings:
            return "honorific"
        return "plain"

    def analyze_honorific(self, sentences: list[SentenceToken]) -> dict:
        labels = [self.detect_honorific(sentence) for sentence in sentences]
        distribution = Counter(labels)
        dominant_label, dominant_count = distribution.most_common(1)[0] if distribution else ("mixed", 0)
        score = self.calculate_consistency_score(distribution, len(labels))

        if len(distribution) > 1 and labels and dominant_count / len(labels) < 0.8:
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