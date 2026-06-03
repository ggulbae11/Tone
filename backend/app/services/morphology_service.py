from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SentenceToken:
    index: int
    text: str
    ending: str


class MorphologyAnalyzer:
    known_endings = [
        "습니다",
        "습니까",
        "합니다",
        "입니다",
        "드립니다",
        "바랍니다",
        "주세요",
        "해주세요",
        "해요",
        "네요",
        "어요",
        "아요",
        "예요",
        "이에요",
        "요",
        "냐",
        "야",
        "줘",
        "할게",
        "을게",
        "어",
        "지",
        "다",
    ]

    def analyze(self, text: str) -> list[SentenceToken]:
        sentences = self._split_sentences(text)
        return [
            SentenceToken(index=index, text=sentence, ending=self.extract_sentence_ending(sentence))
            for index, sentence in enumerate(sentences)
        ]

    def _split_sentences(self, text: str) -> list[str]:
        import re
        normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()

        # 따옴표(", ', 「」, 『』) 내부의 .?! 를 임시 코드포인트로 보호
        _QUOTE_PAIRS = [('"', '"'), ('"', '"'), ("'", "'"), ("'", "'"), ("「", "」"), ("「", "」"), ("『", "』")]
        protected = normalized
        for open_q, close_q in _QUOTE_PAIRS:
            protected = re.sub(
                re.escape(open_q) + r"([^" + re.escape(close_q) + r"]*)" + re.escape(close_q),
                lambda m: open_q + m.group(1).replace(".", "\x01").replace("?", "\x02").replace("!", "\x03") + close_q,
                protected,
            )

        parts = re.split(r"(?<=[.?!。])\s+|(?<=[.?!。])\n+", protected)

        return [
            p.replace("\x01", ".").replace("\x02", "?").replace("\x03", "!").strip()
            for p in parts
            if p.strip()
        ]

    def extract_sentence_ending(self, sentence: str) -> str:
        normalized = sentence.strip().rstrip(".")
        for ending in self.known_endings:
            if normalized.endswith(ending):
                return ending
        return normalized[-2:] if len(normalized) >= 2 else normalized

    def extract_sentence_endings(self, text: str) -> list[str]:
        return [token.ending for token in self.analyze(text)]