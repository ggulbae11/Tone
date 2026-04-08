from __future__ import annotations

import concurrent.futures
import hashlib
import json
from collections import Counter
from typing import Any

from app.config import settings
from app.schemas.analysis import DistributionItem, SentenceAnalysis
from app.services.formality_analyzer import FormalityAnalyzer
from app.services.morphology_service import SentenceToken

try:
    from google import genai
    from google.genai import types
except ImportError:  # pragma: no cover
    genai = None  # type: ignore[assignment]
    types = None  # type: ignore[assignment]


SYSTEM_PROMPT = (
    "당신은 한국어 비즈니스 문서의 격식을 문장 뉘앙스와 문맥까지 고려해 분류하고, "
    "선택한 격식 기준에 맞춰 수정안을 제안하는 편집 전문가다."
)

ANALYSIS_RULES = [
    "문장 끝 표현만 보지 말고 관계, 상황, 압박감, 친밀도, 전체 뉘앙스를 함께 판단한다.",
    "격식 단계는 격식 존댓말, 중립 존댓말, 비격식 반말 중 하나로 분류한다.",
    "수정안은 선택한 격식 기준에 맞지 않는 문장에 대해서만 작성한다.",
    "판단이 애매하면 가장 가까운 단계 하나를 고르고 reason에 근거를 적는다.",
]

FORMALITY_RULE_STEPS = [
    {
        "level": "격식 존댓말",
        "description": "회사, 발표, 면접, 공적인 대화에서 사용하는 딱딱한 존댓말",
        "signals": ["습니다", "습니까", "입니다", "드립니다", "바랍니다"],
    },
    {
        "level": "중립 존댓말",
        "description": "일상 대화, 서비스업 등에서 사용하는 부드러운 존댓말",
        "signals": ["요"],
    },
    {
        "level": "비격식 반말",
        "description": "친근하지만 기본적인 예의를 유지하는 반말",
        "signals": ["냐", "야", "어", "지", "다"],
    },
]

REWRITE_RULES = [
    "원문을 그대로 반복하지 말고 실제로 달라진 문장을 제안한다.",
    "수정 이유는 짧고 구체적으로 쓴다.",
    "문맥을 유지하면서 최소 수정으로 목표 격식에 맞춘다.",
]

FORMALITY_REWRITE_RULE = "선택한 격식 단계에 맞게 종결어미와 요청 표현을 조정한다."


class LLMService:
    def __init__(self) -> None:
        self._client = None
        self._cache: dict[str, Any] = {}
        self._fallback_formality = FormalityAnalyzer()
        if settings.llm_provider == "gemini" and settings.llm_api_key and genai is not None:
            self._client = genai.Client(api_key=settings.llm_api_key)

    def classify_formality(self, sentences: list[SentenceToken]) -> dict[str, Any]:
        cache_key = self._make_classification_cache_key(sentences)
        if cache_key in self._cache:
            return self._cache[cache_key]

        if not sentences or self._client is None:
            fallback = self._build_rule_based_classification(sentences)
            self._cache[cache_key] = fallback
            return fallback

        prompt = self._build_classification_prompt(sentences)
        last_error_name = "UnknownError"

        for model in self._candidate_models():
            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(self._generate_classification_json, model, prompt)
                    raw = future.result(timeout=settings.llm_timeout_seconds)
                classified = self._parse_classification_json(raw, sentences)
                if classified["sentence_labels"]:
                    self._cache[cache_key] = classified
                    return classified
            except concurrent.futures.TimeoutError:
                last_error_name = "TimeoutError"
                continue
            except Exception as exc:  # pragma: no cover
                last_error_name = exc.__class__.__name__
                continue

        fallback = self._build_rule_based_classification(sentences)
        fallback["source"] = f"rule-based-fallback:{last_error_name}"
        self._cache[cache_key] = fallback
        return fallback

    def suggest_rewrites(
        self,
        original_text: str,
        target_level: str,
        sentences: list[SentenceAnalysis],
    ) -> list[dict[str, Any]]:
        cache_key = self._make_rewrite_cache_key(original_text, target_level, sentences)
        if cache_key in self._cache:
            return self._cache[cache_key]

        if not sentences:
            return []

        if self._client is None:
            fallback = self._build_rule_based_rewrites(target_level, sentences)
            self._cache[cache_key] = fallback
            return fallback

        prompt = self._build_rewrite_prompt(target_level, sentences)
        last_error_name = "UnknownError"

        for model in self._candidate_models():
            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(self._generate_rewrite_json, model, prompt)
                    raw = future.result(timeout=settings.llm_timeout_seconds)
                rewrites = self._parse_rewrite_json(raw, target_level)
                if rewrites:
                    self._cache[cache_key] = rewrites
                    return rewrites
            except concurrent.futures.TimeoutError:
                last_error_name = "TimeoutError"
                continue
            except Exception as exc:  # pragma: no cover
                last_error_name = exc.__class__.__name__
                continue

        fallback = self._build_rule_based_rewrites(target_level, sentences)
        if fallback:
            fallback[0]["reason"] = f"AI 응답을 받지 못해 규칙 기반 제안으로 대체했습니다: {last_error_name}. {fallback[0]['reason']}"
        self._cache[cache_key] = fallback
        return fallback

    def _build_rule_guide(self) -> str:
        lines = [f"[System Prompt]\n{SYSTEM_PROMPT}", "[Analysis Rules]"]
        lines.extend(f"- {rule}" for rule in ANALYSIS_RULES)
        lines.append("[Formality Levels]")
        for item in FORMALITY_RULE_STEPS:
            lines.append(f"- {item['level']}: {item['description']} / hints={', '.join(item['signals'])}")
        lines.append("[Rewrite Rules]")
        lines.extend(f"- {rule}" for rule in REWRITE_RULES)
        return "\n".join(lines)

    def _generate_classification_json(self, model: str, prompt: str) -> str:
        if self._client is None:
            return ""
        config: dict[str, Any] = {
            "temperature": 0.1,
            "max_output_tokens": 900,
            "response_mime_type": "application/json",
            "response_json_schema": {
                "type": "object",
                "properties": {
                    "sentences": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "sentence_index": {"type": "integer"},
                                "label": {"type": "string"},
                                "confidence": {"type": "number"},
                                "reason": {"type": "string"}
                            },
                            "required": ["sentence_index", "label", "confidence", "reason"]
                        }
                    }
                },
                "required": ["sentences"]
            }
        }
        if types is not None:
            config["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
        response = self._client.models.generate_content(model=model, contents=prompt, config=config)
        text = getattr(response, "text", None)
        return text if isinstance(text, str) else str(text or "")

    def _generate_rewrite_json(self, model: str, prompt: str) -> str:
        if self._client is None:
            return ""
        config: dict[str, Any] = {
            "temperature": 0.2,
            "max_output_tokens": 700,
            "response_mime_type": "application/json",
            "response_json_schema": {
                "type": "object",
                "properties": {
                    "rewrites": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "sentence_index": {"type": "integer"},
                                "original_sentence": {"type": "string"},
                                "current_formality": {"type": "string"},
                                "target_formality": {"type": "string"},
                                "reason": {"type": "string"},
                                "suggested_sentence": {"type": "string"},
                                "source": {"type": "string"}
                            },
                            "required": ["sentence_index", "original_sentence", "current_formality", "target_formality", "reason", "suggested_sentence", "source"]
                        }
                    }
                },
                "required": ["rewrites"]
            }
        }
        if types is not None:
            config["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
        response = self._client.models.generate_content(model=model, contents=prompt, config=config)
        text = getattr(response, "text", None)
        return text if isinstance(text, str) else str(text or "")

    def _build_classification_prompt(self, sentences: list[SentenceToken]) -> str:
        sentence_lines = "\n".join(f"- index={sentence.index}, text={sentence.text}" for sentence in sentences)
        return (
            f"{self._build_rule_guide()}\n\n"
            "[Current Task]\n아래 문장 각각을 문장 끝 표현만이 아니라 어휘, 압박감, 친밀도, 공적/사적 상황의 뉘앙스를 함께 고려해 분류하세요.\n"
            "반드시 JSON만 출력하세요.\n\n"
            f"대상 문장 목록:\n{sentence_lines}"
        )

    def _build_rewrite_prompt(self, target_level: str, sentences: list[SentenceAnalysis]) -> str:
        sentence_lines = "\n".join(f"- index={sentence.index}, formality={sentence.formality}, text={sentence.text}" for sentence in sentences)
        return (
            f"{self._build_rule_guide()}\n\n"
            f"[Current Task]\n- target_formality={target_level}\n- rewrite_rule={FORMALITY_REWRITE_RULE}\n\n"
            "선택한 격식 기준에 맞지 않는 문장만 골라 수정안을 작성하세요. 반드시 JSON만 출력하세요.\n\n"
            f"대상 문장 목록:\n{sentence_lines}"
        )

    def _parse_classification_json(self, raw: str, sentences: list[SentenceToken]) -> dict[str, Any]:
        payload = json.loads(raw)
        items = payload.get("sentences", []) if isinstance(payload, dict) else []
        allowed = {item["level"] for item in FORMALITY_RULE_STEPS}
        by_index: dict[int, dict[str, Any]] = {}
        for item in items:
            if not isinstance(item, dict):
                continue
            index = int(item.get("sentence_index", -1))
            label = str(item.get("label", "")).strip()
            if index < 0 or label not in allowed:
                continue
            by_index[index] = {
                "label": label,
                "confidence": float(item.get("confidence", 0.0)),
                "reason": str(item.get("reason", "")).strip(),
            }
        labels: list[str] = []
        reasons: list[str] = []
        confidences: list[float] = []
        for sentence in sentences:
            matched = by_index.get(sentence.index)
            if matched is None:
                fallback_label = self._fallback_formality.detect_formality(sentence.ending)
                labels.append(fallback_label)
                reasons.append("AI 응답에 누락되어 규칙 기반 라벨로 보완했습니다.")
                confidences.append(0.0)
            else:
                labels.append(matched["label"])
                reasons.append(matched["reason"])
                confidences.append(matched["confidence"])
        distribution = Counter(labels)
        dominant_label, dominant_count = distribution.most_common(1)[0] if distribution else ("mixed", 0)
        if len(distribution) >= 3 or (labels and dominant_count / len(labels) < 0.7):
            dominant_label = "mixed"
        score = self._calculate_consistency_score(distribution, len(labels))
        return {
            "dominant_level": dominant_label,
            "score": score,
            "distribution": [DistributionItem(label=label, count=count) for label, count in distribution.items()],
            "sentence_labels": labels,
            "sentence_reasons": reasons,
            "sentence_confidences": confidences,
            "source": "ai",
        }

    def _build_rule_based_classification(self, sentences: list[SentenceToken]) -> dict[str, Any]:
        labels = [self._fallback_formality.detect_formality(sentence.ending) for sentence in sentences]
        distribution = Counter(labels)
        dominant_label, dominant_count = distribution.most_common(1)[0] if distribution else ("mixed", 0)
        if len(distribution) >= 3 or (labels and dominant_count / len(labels) < 0.7):
            dominant_label = "mixed"
        return {
            "dominant_level": dominant_label,
            "score": self._calculate_consistency_score(distribution, len(labels)),
            "distribution": [DistributionItem(label=label, count=count) for label, count in distribution.items()],
            "sentence_labels": labels,
            "sentence_reasons": ["규칙 기반 fallback 분류입니다." for _ in sentences],
            "sentence_confidences": [0.0 for _ in sentences],
            "source": "rule-based",
        }

    def _build_rule_based_rewrites(self, target_level: str, sentences: list[SentenceAnalysis]) -> list[dict[str, Any]]:
        rewrites: list[dict[str, Any]] = []
        for sentence in sentences:
            suggested = self._force_rewrite_sentence(sentence.text, target_level)
            if self._normalize_sentence(suggested) == self._normalize_sentence(sentence.text):
                continue
            rewrites.append({
                "sentence_index": sentence.index,
                "original_sentence": sentence.text,
                "current_formality": sentence.formality,
                "target_formality": target_level,
                "reason": FORMALITY_REWRITE_RULE,
                "suggested_sentence": suggested,
                "source": "rule-based",
            })
        return rewrites

    def _parse_rewrite_json(self, raw: str, target_level: str) -> list[dict[str, Any]]:
        payload = json.loads(raw)
        items = payload.get("rewrites", []) if isinstance(payload, dict) else []
        normalized: list[dict[str, Any]] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            original_sentence = str(item.get("original_sentence", "")).strip()
            suggested_sentence = str(item.get("suggested_sentence", "")).strip()
            current_formality = str(item.get("current_formality", "")).strip()
            reason = str(item.get("reason", "선택한 격식 기준에 맞게 문장을 조정했습니다.")).strip()
            source = str(item.get("source", "ai")).strip() or "ai"
            if not original_sentence:
                continue
            if not suggested_sentence or self._normalize_sentence(suggested_sentence) == self._normalize_sentence(original_sentence):
                suggested_sentence = self._force_rewrite_sentence(original_sentence, target_level)
                source = "rule-based"
            if self._normalize_sentence(suggested_sentence) == self._normalize_sentence(original_sentence):
                continue
            normalized.append({
                "sentence_index": int(item.get("sentence_index", 0)),
                "original_sentence": original_sentence,
                "current_formality": current_formality,
                "target_formality": target_level,
                "reason": reason,
                "suggested_sentence": suggested_sentence,
                "source": "ai" if source == "ai" else "rule-based",
            })
        return normalized

    def _force_rewrite_sentence(self, sentence: str, target_level: str) -> str:
        stripped = sentence.strip()
        has_period = stripped.endswith(".")
        bare = stripped[:-1] if has_period else stripped
        rewritten = bare
        replacements = [
            ("보내줘", "보내요", "보내주세요", "보내드리겠습니다"),
            ("확인해줘", "확인해요", "확인해주세요", "확인해 주시기 바랍니다"),
            ("부탁해", "부탁해요", "부탁드립니다", "부탁드립니다"),
            ("알려줘", "알려줘요", "알려주세요", "알려주시기 바랍니다"),
            ("검토해줘", "검토해요", "검토 부탁드립니다", "검토해 주시기 바랍니다"),
            ("왔어", "왔어요", "왔어요", "도착했습니다"),
            ("했어", "했어요", "했어요", "수행했습니다"),
        ]
        if target_level == "격식 존댓말":
            for plain, neutral, _, formal in replacements:
                rewritten = rewritten.replace(plain, formal)
                rewritten = rewritten.replace(neutral, formal)
            if rewritten.endswith("요"):
                rewritten = rewritten[:-1] + "습니다"
            elif rewritten.endswith("다"):
                rewritten = rewritten[:-1] + "습니다"
            elif not rewritten.endswith(("습니다", "입니다", "드립니다", "바랍니다")):
                rewritten = rewritten + " 바랍니다"
        elif target_level == "중립 존댓말":
            for plain, neutral, polite, formal in replacements:
                rewritten = rewritten.replace(plain, neutral)
                rewritten = rewritten.replace(polite, neutral)
                rewritten = rewritten.replace(formal, neutral)
            if rewritten.endswith("다"):
                rewritten = rewritten[:-1] + "요"
        elif target_level == "비격식 반말":
            for plain, neutral, polite, formal in replacements:
                rewritten = rewritten.replace(formal, plain)
                rewritten = rewritten.replace(polite, plain)
                rewritten = rewritten.replace(neutral, plain)
            rewritten = rewritten.replace("입니다", "야").replace("습니다", "다")
            if rewritten.endswith("냐"):
                rewritten = rewritten[:-1] + "다"
        rewritten = rewritten.strip()
        if not rewritten:
            rewritten = bare
        if has_period and not rewritten.endswith("."):
            rewritten += "."
        return rewritten

    def _candidate_models(self) -> list[str]:
        models = [settings.llm_model]
        models.extend(model.strip() for model in settings.llm_fallback_models.split(",") if model.strip())
        deduped: list[str] = []
        for model in models:
            if model not in deduped:
                deduped.append(model)
        return deduped

    def _calculate_consistency_score(self, distribution: Counter[str], sentence_count: int) -> float:
        if sentence_count == 0:
            return 0.0
        dominant_count = distribution.most_common(1)[0][1] if distribution else 0
        ratio = dominant_count / sentence_count
        return round(50 + ratio * 50, 1)

    def _make_classification_cache_key(self, sentences: list[SentenceToken]) -> str:
        payload = [{"index": s.index, "text": s.text, "ending": s.ending} for s in sentences]
        serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        return "classify:" + hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def _make_rewrite_cache_key(self, original_text: str, target_level: str, sentences: list[SentenceAnalysis]) -> str:
        payload = {"text": original_text, "target_level": target_level, "sentences": [{"index": s.index, "text": s.text, "formality": s.formality} for s in sentences]}
        serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        return "rewrite:" + hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def _normalize_sentence(self, sentence: str) -> str:
        return " ".join(sentence.strip().rstrip(".").split())