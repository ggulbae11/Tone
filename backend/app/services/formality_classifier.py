from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

_MODELS_DIR = Path(__file__).parent.parent.parent / "models"
_MODEL_DIR = _MODELS_DIR / "formality_classifier"
_RULES_PATH = _MODELS_DIR / "formality_rules.json"

_ID2LABEL: dict[int, str] = {
    0: "habsho",
    1: "haeyoche",
    2: "hageche",
    3: "haeche",
    4: "haerache",
    5: "plain",
}

_FORMALITY_KO: dict[str, str] = {
    "habsho":   "합쇼체",
    "haeyoche": "해요체",
    "hageche":  "하게체",
    "haeche":   "해체",
    "haerache": "해라체",
    "plain":    "평서체",
    "unknown":  "알 수 없음",
}

# LLM·FormalityAnalyzer와 동일한 용어로 통일
_FORMALITY_GROUP: dict[str, str] = {
    "habsho":   "격식 존댓말",
    "haeyoche": "중립 존댓말",
    "hageche":  "비격식 반말",
    "haeche":   "비격식 반말",
    "haerache": "비격식 반말",
    "plain":    "중립",
    "unknown":  "알 수 없음",
}

MAX_LENGTH = 64


def _rule_override(text: str, ml_label: str) -> str:
    """ML 예측을 RAW_ENDINGS 규칙으로 검증, 충돌 시 규칙 우선."""
    normalized = _normalize_jamo(text.strip().rstrip(".?! "))
    for suffix, level in _RAW_ENDINGS:
        if normalized.endswith(suffix):
            return level   # 규칙 매칭 → 규칙 우선
    return ml_label        # 매칭 없음 → ML 그대로


def _check_consistency(results: list[dict]) -> list[dict]:
    """dominant 그룹과 다른 문장에 is_formality_consistent=False 표시."""
    known = [r for r in results if r["formality"] != "unknown"]
    if not known:
        for r in results:
            r["is_formality_consistent"] = None
        return results
    dominant_group = Counter(_FORMALITY_GROUP[r["formality"]] for r in known).most_common(1)[0][0]
    for r in results:
        if r["formality"] == "unknown":
            r["is_formality_consistent"] = None
        else:
            r["is_formality_consistent"] = (_FORMALITY_GROUP[r["formality"]] == dominant_group)
    return results


# ── ML 분류기 ──────────────────────────────────────────────────────────────────

class FormalityMLClassifier:
    def __init__(self) -> None:
        import torch
        from transformers import AutoTokenizer

        int8_path = _MODEL_DIR / "model_int8.pt"
        if int8_path.exists():
            self._model = torch.load(int8_path, map_location="cpu", weights_only=False)
        else:
            from transformers import AutoModelForSequenceClassification
            self._model = AutoModelForSequenceClassification.from_pretrained(str(_MODEL_DIR))
        self._model.eval()

        self._tokenizer = AutoTokenizer.from_pretrained(str(_MODEL_DIR))
        self._tokenizer.truncation_side = "left"

    def classify_batch(self, texts: list[str]) -> list[dict]:
        import torch
        inputs = self._tokenizer(
            texts,
            return_tensors="pt",
            truncation=True,
            padding=True,
            max_length=MAX_LENGTH,
        )
        with torch.no_grad():
            logits = self._model(**inputs).logits
        probs = torch.softmax(logits, dim=-1)
        indices = probs.argmax(dim=-1).tolist()
        confidences = probs.max(dim=-1).values.tolist()
        results = []
        for text, idx, conf in zip(texts, indices, confidences):
            ml_label = _ID2LABEL[idx]
            final_label = _rule_override(text, ml_label)
            results.append({
                "formality": final_label,
                "formality_ko": _FORMALITY_KO[final_label],
                "formality_confidence": round(float(conf), 4) if final_label == ml_label else None,
            })
        return _check_consistency(results)


# ── 규칙 기반 폴백 분류기 ──────────────────────────────────────────────────────

# formality_rules.json의 kiwi_ef는 형태소 분석 토큰이라 원문 직접 매칭 불가.
# 원문 어미 직접 매칭용 보조 테이블 (긴 패턴 우선 적용)
_RAW_ENDINGS: list[tuple[str, str]] = sorted([
    # habsho (합쇼체)
    ("으십시오", "habsho"), ("십시오", "habsho"),
    ("읍시다", "habsho"), ("봅시다", "habsho"), ("ㅂ시다", "habsho"),
    ("습니까", "habsho"), ("됩니까", "habsho"), ("입니까", "habsho"),
    ("습니다", "habsho"), ("됩니다", "habsho"), ("합니다", "habsho"),
    ("입니다", "habsho"), ("드립니다", "habsho"), ("바랍니다", "habsho"),
    ("옵니다", "habsho"), ("랍니다", "habsho"),
    ("니다", "habsho"), ("니까", "habsho"),   # 나머지 ~니다/~니까 패턴 포괄
    # haeyoche (해요체)
    ("으세요", "haeyoche"), ("주세요", "haeyoche"), ("세요", "haeyoche"),
    ("해주세요", "haeyoche"),
    ("어요", "haeyoche"), ("아요", "haeyoche"), ("여요", "haeyoche"),
    ("이에요", "haeyoche"), ("예요", "haeyoche"), ("에요", "haeyoche"),
    ("네요", "haeyoche"), ("군요", "haeyoche"), ("죠", "haeyoche"),
    ("거든요", "haeyoche"), ("잖아요", "haeyoche"),
    ("ㄹ게요", "haeyoche"), ("을게요", "haeyoche"),
    ("ㄹ까요", "haeyoche"), ("을까요", "haeyoche"),
    ("ㄹ래요", "haeyoche"), ("을래요", "haeyoche"),
    ("나요", "haeyoche"), ("지요", "haeyoche"),
    ("던데요", "haeyoche"), ("는데요", "haeyoche"), ("은데요", "haeyoche"),
    ("대요", "haeyoche"),
], key=lambda x: -len(x[0]))

_TRAILING_TO_COMPAT = {
    "ᆨ": "ㄱ", "ᆩ": "ㄲ", "ᆪ": "ㄳ", "ᆫ": "ㄴ", "ᆬ": "ㄵ", "ᆭ": "ㄶ",
    "ᆮ": "ㄷ", "ᆯ": "ㄹ", "ᆰ": "ㄺ", "ᆱ": "ㄻ", "ᆲ": "ㄼ", "ᆳ": "ㄽ",
    "ᆴ": "ㄾ", "ᆵ": "ㄿ", "ᆶ": "ㅀ", "ᆷ": "ㅁ", "ᆸ": "ㅂ", "ᆹ": "ㅃ",
    "ᆺ": "ㅅ", "ᆻ": "ㅆ", "ᆼ": "ㅇ", "ᆽ": "ㅈ", "ᆾ": "ㅊ", "ᆿ": "ㅋ",
    "ᇀ": "ㅌ", "ᇁ": "ㅍ", "ᇂ": "ㅎ",
}


def _normalize_jamo(s: str) -> str:
    return "".join(_TRAILING_TO_COMPAT.get(c, c) for c in s)


class FormalityRuleClassifier:
    def __init__(self) -> None:
        with open(_RULES_PATH, encoding="utf-8") as f:
            rules = json.load(f)
        self._ef_map: dict[str, str] = {}
        for level, info in rules["formality_levels"].items():
            for ef in info.get("kiwi_ef", []):
                self._ef_map[_normalize_jamo(ef.strip())] = level
            for ef in info.get("kiwi_ef_connective", []):
                self._ef_map[_normalize_jamo(ef.strip())] = level

    def _detect(self, text: str) -> str:
        normalized = _normalize_jamo(text.strip().rstrip(".?! "))
        # 1순위: 원문 직접 매칭 테이블 (긴 패턴 우선)
        for suffix, level in _RAW_ENDINGS:
            if normalized.endswith(suffix):
                return level
        # 2순위: formality_rules.json EF맵 (형태소 토큰, 일부만 매칭됨)
        for length in range(min(6, len(normalized)), 0, -1):
            suffix = normalized[-length:]
            lvl = self._ef_map.get(suffix)
            if lvl:
                return lvl
        return "unknown"

    def classify_batch(self, texts: list[str]) -> list[dict]:
        results = [
            {
                "formality": self._detect(t),
                "formality_ko": _FORMALITY_KO[self._detect(t)],
                "formality_confidence": None,
            }
            for t in texts
        ]
        return _check_consistency(results)


# ── 싱글턴 팩토리 ──────────────────────────────────────────────────────────────

_instance: FormalityMLClassifier | FormalityRuleClassifier | None = None
_load_attempted = False


def get_formality_classifier() -> FormalityMLClassifier | FormalityRuleClassifier | None:
    """ML 모델 우선, 실패 시 rules 폴백, rules도 없으면 None."""
    global _instance, _load_attempted
    if _load_attempted:
        return _instance
    _load_attempted = True

    if _MODEL_DIR.exists():
        try:
            _instance = FormalityMLClassifier()
            return _instance
        except Exception:
            pass

    if _RULES_PATH.exists():
        try:
            _instance = FormalityRuleClassifier()
            return _instance
        except Exception:
            pass

    return None
