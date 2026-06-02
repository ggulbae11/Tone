from __future__ import annotations


class FormalityAnalyzer:
    formal_honorific_endings = {"습니다", "습니까", "합니다", "입니다", "드립니다", "바랍니다"}
    neutral_honorific_endings = {"요"}
    informal_plain_endings = {"냐", "야", "줘", "할게", "을게", "어", "지", "다"}

    def detect_formality(self, ending: str) -> str:
        if ending in self.formal_honorific_endings:
            return "격식 존댓말"
        if ending in self.neutral_honorific_endings:
            return "중립 존댓말"
        if ending in self.informal_plain_endings:
            return "비격식 반말"
        return "중립 존댓말"