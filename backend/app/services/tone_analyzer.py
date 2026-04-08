from __future__ import annotations


class ToneAnalyzer:
    respectful_markers = ["감사", "죄송", "양해", "부탁", "도움"]
    directive_markers = ["반드시", "즉시", "제출 바랍니다", "확인 바랍니다"]
    friendly_markers = ["좋아요", "편하게", "반가워", "고마워"]
    requesting_markers = ["부탁드립니다", "확인 부탁", "가능할까요", "해주시면"]

    def analyze(self, text: str) -> dict:
        respectful_score = sum(marker in text for marker in self.respectful_markers)
        directive_score = sum(marker in text for marker in self.directive_markers)
        friendly_score = sum(marker in text for marker in self.friendly_markers)
        requesting_score = sum(marker in text for marker in self.requesting_markers)

        label = "neutral"
        confidence = 0.55

        if requesting_score:
            label, confidence = "requesting", 0.82
        elif directive_score:
            label, confidence = "directive", 0.78
        elif respectful_score:
            label, confidence = "respectful", 0.74
        elif friendly_score:
            label, confidence = "friendly", 0.68

        return {"label": label, "confidence": confidence}