from __future__ import annotations

import concurrent.futures
import hashlib
import json
from typing import Any

from app.config import settings
from app.services.formality_analyzer import FormalityAnalyzer
from app.services.morphology_service import SentenceToken

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None  # type: ignore[assignment,misc]


SYSTEM_PROMPT_CONTEXT = (
    "당신은 한국어 텍스트를 분석하는 언어 전문가입니다. "
    "주어진 글의 전체적인 맥락(상황, 관계, 목적 등)을 파악하여 구조화된 JSON으로 반환합니다. "
    "반드시 유효한 JSON만 출력하세요."
)

SYSTEM_PROMPT_SENTENCES = (
    "당신은 한국어 텍스트를 분석하는 언어 전문가입니다. "
    "확정된 맥락을 기준으로 각 문장이 맥락의 모든 요소와 하나하나 일치하는지 판단하고, "
    "맞지 않는 문장에 수정안을 제안합니다. "
    "수정안의 목표는 이 글의 목소리·결·리듬을 살리면서 "
    "맥락·톤이 일관된 자연스러운 완성된 글을 만드는 것입니다. "
    "일반적으로 더 나은 문장이 아니라, 이 텍스트 안에서 자연스러운 문장이 기준입니다. "
    "반드시 유효한 JSON만 출력하세요."
)

SYSTEM_PROMPT_FLOW = (
    "당신은 한국어 텍스트의 전체적인 흐름과 응집성을 검토하는 편집 전문가입니다. "
    "개별 문장이 맥락 요소와 일치하더라도 문장 간 연결과 전체 흐름에 문제가 있는지 판단합니다. "
    "수정안의 목표는 이 글의 목소리·결·리듬을 살리면서 "
    "흐름이 자연스럽게 이어지는 완성된 글을 만드는 것입니다. "
    "일반적으로 더 나은 문장이 아니라, 이 텍스트 안에서 자연스러운 문장이 기준입니다. "
    "반드시 유효한 JSON만 출력하세요."
)

# 암묵적 문체 특성 추출 기준 (프롬프트 삽입용)
_IMPLICIT_STYLE_CRITERIA = """
[암묵적 문체 특성 추출 기준]
다음 조건을 반드시 따르세요.

━━━ 핵심 원칙 ━━━
분석 요소 값은 글의 '방향'(절제됨, 격식 높음 등)을 설명할 뿐,
'어떤 구체적 표현으로 구현되는지'는 설명하지 못한다.
emotional_tone=절제됨이라고 해도, 그 절제가 특정 어구 패턴으로 반복 구현되고 있다면 추출한다.

━━━ 즉시 null (단, P2·P3 해당 시 null 처리하지 않음) ━━━
- 완성된 문장이 3개 미만
- 공문서 / 법적 문서 / 학술 논문 / 행정 양식
- 전체 격식·분위기가 요소 값으로 설명되고, P2·P3도 해당하지 않는 경우
- 애매한 경우 → null

━━━ 추출 조건 ━━━
P1. 실제 언어 패턴이 요소 값만으로 예측되지 않을 때

P2. 비슷한 역할을 하는 표현·구조가 2곳 이상 반복될 때
    (정확히 같은 표현이 아니어도, 동일한 기능을 하면 해당)
    판단 질문: "이 요소 값들을 아는 사람이 글을 새로 쓴다면,
    이런 구체적 표현 패턴을 자연스럽게 선택할까?" → 아니라면 추출

P3. 특정 커뮤니티·세대·직군 특유 어휘가 2곳 이상 반복될 때

━━━ 판단 예시 ━━━
[추출 O] "점심은 먹었어? / 생각났어, 바쁘면 괜찮고. / 주말에 뭐 해? 그냥 궁금해서."
→ emotional_tone=절제됨으로 태그되더라도,
  관심 표현 직후 감정을 차단하는 어구가 반복되는 것은 P2 해당.
  올바른 value 예시: "관심이나 감정을 내비친 직후 즉시 거리두기로 마무리하는 패턴, 감정 직접 언급 없음"
  잘못된 value 예시: "'바쁘면 괜찮고', '그냥 궁금해서' 표현 사용" ← 글의 내용을 그대로 옮긴 것

[추출 O] "야 오늘 ㄹㅇ 힘들었음. 팀장이 또 뒤집었고 멘탈 탈탈. 칼퇴 물 건너갔음."
→ 직장인 커뮤니티 특유 어휘 반복 → P3 해당.
  올바른 value 예시: "직장인 온라인 커뮤니티 특유의 줄임말·과장 표현 일관 사용"
  잘못된 value 예시: "'ㄹㅇ', '멘탈 탈탈', '칼퇴' 표현 사용" ← 글의 내용을 그대로 옮긴 것

[추출 X] "보고서 완료했습니다. 확인 부탁드립니다. 추가 수정 시 말씀해주세요."
→ 표준 업무 존댓말. formality=높음, power_distance=큰 으로 충분히 예측 가능 → null.

━━━ 추출 시 작성 ━━━
- value: 관찰한 증거를 바탕으로 도출한 '패턴·규칙'을 서술한다.
  글에서 찾은 특정 표현을 그대로 나열하지 말 것.
  "어떤 표현을 썼는가"가 아니라 "어떤 방식으로 쓰는가"를 설명할 것.
  (좋은 예: "감정 표현 후 즉시 거리두기로 마무리하는 패턴")
  (나쁜 예: "'그냥', '바쁘면 괜찮고' 등 표현 반복")
- reason: 이 패턴이 요소 값만으로 재현되지 않는 이유 한 줄로
""".strip()


class LLMService:
    def __init__(self) -> None:
        self._client = None
        self._cache: dict[str, Any] = {}
        self._fallback_formality = FormalityAnalyzer()
        if settings.llm_provider == "openai" and settings.llm_api_key and OpenAI is not None:
            self._client = OpenAI(api_key=settings.llm_api_key)

    # ── 1단계: 맥락 추출 ──────────────────────────────────────────────────────

    def extract_context(self, text: str, factors: list[dict[str, str]]) -> dict[str, Any]:
        cache_key = "ctx:" + self._hash(text, [f["key"] for f in factors])
        if cache_key in self._cache:
            return self._cache[cache_key]

        if self._client is None:
            result = self._rule_based_context(factors)
            self._cache[cache_key] = result
            return result

        prompt = self._build_extract_context_prompt(text, factors)
        last_err = "UnknownError"
        for model in self._candidate_models():
            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                    raw = ex.submit(self._call, SYSTEM_PROMPT_CONTEXT, model, prompt).result(
                        timeout=settings.llm_timeout_seconds
                    )
                result = self._parse_context(raw, factors)
                if result["context"]:
                    self._cache[cache_key] = result
                    return result
            except concurrent.futures.TimeoutError:
                last_err = "TimeoutError"
            except Exception as exc:  # pragma: no cover
                last_err = exc.__class__.__name__

        result = self._rule_based_context(factors)
        result["source"] = f"rule-based-fallback:{last_err}"
        self._cache[cache_key] = result
        return result

    def _build_extract_context_prompt(self, text: str, factors: list[dict[str, str]]) -> str:
        factor_lines = "\n".join(f"- {f['label']} ({f['key']}): {f['description']}" for f in factors)
        context_schema = ", ".join('"' + f["key"] + '": "..."' for f in factors)
        return (
            f"[분석 요소]\n{factor_lines}\n\n"
            f"[전체 원문]\n{text}\n\n"
            "[지시]\n"
            "1. 전체 원문을 읽고 각 분석 요소의 값을 구체적으로 파악하세요.\n"
            "2. 글 전체의 맥락을 overall_summary에 한 문장으로 요약하세요.\n"
            f"3. 암묵적 문체 특성(implicit_style)을 아래 기준에 따라 추출하세요.\n\n"
            f"{_IMPLICIT_STYLE_CRITERIA}\n\n"
            "4. JSON만 출력하세요.\n\n"
            "[출력 형식]\n"
            "{\n"
            f'  "context": {{ {context_schema} }},\n'
            '  "overall_summary": "...",\n'
            '  "implicit_style": { "value": "...", "reason": "..." }\n'
            '  // 추출 불필요 시: "implicit_style": null\n'
            "}"
        )

    def _parse_context(self, raw: str, factors: list[dict[str, str]]) -> dict[str, Any]:
        payload = json.loads(raw)
        context_data = payload.get("context", {}) if isinstance(payload, dict) else {}
        overall_summary = str(payload.get("overall_summary", "")).strip()

        implicit_style = None
        raw_is = payload.get("implicit_style")
        if isinstance(raw_is, dict):
            value = str(raw_is.get("value", "")).strip()
            reason = str(raw_is.get("reason", "")).strip()
            if value:
                implicit_style = {"value": value, "reason": reason}

        return {
            "context": context_data,
            "overall_summary": overall_summary,
            "implicit_style": implicit_style,
            "source": "ai",
        }

    def _rule_based_context(self, factors: list[dict[str, str]]) -> dict[str, Any]:
        return {
            "context": {f["key"]: "분석 불가 (API 키 설정 필요)" for f in factors},
            "overall_summary": "AI 연결이 필요합니다.",
            "implicit_style": None,
            "source": "rule-based",
        }

    # ── 2단계: 확정된 맥락으로 문장 분석 ─────────────────────────────────────

    def check_sentences_against_context(
        self,
        text: str,
        sentences: list[SentenceToken],
        context: dict[str, str],
        factors: list[dict[str, str]],
        implicit_style_value: str = "",
    ) -> dict[str, Any]:
        cache_key = "sent:" + self._hash(text, context, implicit_style_value)
        if cache_key in self._cache:
            return self._cache[cache_key]

        if not sentences or self._client is None:
            result = self._rule_based_sentences(sentences, factors)
            self._cache[cache_key] = result
            return result

        prompt = self._build_sentences_prompt(text, sentences, context, factors, implicit_style_value)
        last_err = "UnknownError"
        for model in self._candidate_models():
            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                    raw = ex.submit(self._call, SYSTEM_PROMPT_SENTENCES, model, prompt).result(
                        timeout=settings.llm_timeout_seconds
                    )
                result = self._parse_sentences(raw, sentences, factors)
                if result["sentences"]:
                    self._cache[cache_key] = result
                    return result
            except concurrent.futures.TimeoutError:
                last_err = "TimeoutError"
            except Exception as exc:  # pragma: no cover
                last_err = exc.__class__.__name__

        result = self._rule_based_sentences(sentences, factors)
        result["source"] = f"rule-based-fallback:{last_err}"
        self._cache[cache_key] = result
        return result

    def _build_sentences_prompt(
        self,
        text: str,
        sentences: list[SentenceToken],
        context: dict[str, str],
        factors: list[dict[str, str]],
        implicit_style_value: str = "",
    ) -> str:
        context_lines = "\n".join(
            f"- {f['label']} ({f['key']}): {context.get(f['key'], '미정')}" for f in factors
        )
        factor_keys = ", ".join(f'"{f["key"]}"' for f in factors)
        sentence_lines = "\n".join(f'- index={s.index}, text="{s.text}"' for s in sentences)

        implicit_section = ""
        if implicit_style_value.strip():
            implicit_section = (
                "\n[암묵적 문체 특성 — 명시적 요소 외 이 글의 고유한 문체 패턴]\n"
                f"{implicit_style_value}\n"
            )

        implicit_instruction = ""
        implicit_output_fields = (
            '      "has_implicit_style_issue": false,\n'
            '      "implicit_style_reason": "",\n'
            '      "implicit_style_rewrite": ""\n'
        )
        if implicit_style_value.strip():
            implicit_instruction = (
                "6. 위 암묵적 문체 특성도 각 문장이 지키고 있는지 확인하세요.\n"
                "   - 위반 시 has_implicit_style_issue=true, implicit_style_reason에 이유를 작성하세요.\n"
                "   - implicit_style_rewrite 원칙: 문체와 맞지 않는 표현만 최소한으로 수정하고,\n"
                "     글의 말투·리듬·구체적 디테일은 그대로 보존하세요.\n"
                "     이 글 특유의 결(거칠거나 투박한 표현 포함)을 살린 채 일관성만 맞추세요.\n"
                "     해당 문장 하나의 내용만 포함하고 앞뒤 문장과 합치지 마세요.\n"
                "   - 명시적 요소 위반(is_consistent=false)인 문장은 has_implicit_style_issue 판단을 생략하고 false로 두세요.\n"
            )

        return (
            "[확정된 맥락 — 사용자가 검토·수정 완료한 값입니다. 이 값을 기준으로 분석하세요]\n"
            f"{context_lines}\n"
            f"{implicit_section}\n"
            f"[전체 원문]\n{text}\n\n"
            f"[문장 목록]\n{sentence_lines}\n\n"
            "[지시]\n"
            f"1. 각 문장을 위 맥락의 요소 하나하나({factor_keys})와 개별적으로 대조하세요.\n"
            "2. 단 하나의 요소라도 확정된 값과 맞지 않으면 is_consistent=false로 판단하세요.\n"
            "3. violated_factors에 맞지 않은 요소의 key를 배열로 나열하세요 (일치하면 []).\n"
            "4. inconsistency_reason에 어떤 요소가 왜 맞지 않는지 구체적으로 설명하세요.\n"
            "5. suggested_rewrite 작성 원칙 — 반드시 따르세요:\n"
            "   [무엇을 고치는가]\n"
            "   - 맥락과 맞지 않는 표현만 최소한으로 수정하세요.\n"
            "   - 문제없는 부분은 원문 표현을 그대로 유지하세요.\n"
            "   [무엇을 보존하는가]\n"
            "   - 글의 말투·리듬·어조를 그대로 살리세요.\n"
            "   - 장소·인물·상황 등 구체적 디테일을 삭제하거나 일반화하지 마세요.\n"
            "   - 거칠거나 투박한 표현이 이 글의 특성이라면, 수정 후에도 그 결을 유지하세요.\n"
            "   [목표]\n"
            "   - 이 글의 목소리와 결을 살리면서, 맥락·톤이 일관된 자연스러운 완성된 글을 만드세요.\n"
            "   - 일반적으로 '더 나은 문장'이 아니라, '이 텍스트 안에서 자연스러운 문장'이 기준입니다.\n"
            "   - 예) 반말 카톡에서 한 문장만 존댓말이면 → 그 문장만 반말로 바꾸고 나머지는 그대로\n"
            "   [형식]\n"
            "   - 해당 문장 하나의 내용만 포함하세요. 앞뒤 문장과 합치지 마세요.\n"
            f"{implicit_instruction}"
            "일치하는 문장은 violated_factors=[], inconsistency_reason=\"\", suggested_rewrite=\"\"로 두세요.\n\n"
            "[출력 형식 — 반드시 이 JSON 구조만 출력]\n"
            "{\n"
            '  "sentences": [\n'
            "    {\n"
            '      "sentence_index": 0,\n'
            '      "is_consistent": true,\n'
            '      "violated_factors": [],\n'
            '      "inconsistency_reason": "",\n'
            '      "suggested_rewrite": "",\n'
            f"{implicit_output_fields}"
            "    }\n"
            "  ]\n"
            "}"
        )

    def _parse_sentences(
        self,
        raw: str,
        sentences: list[SentenceToken],
        factors: list[dict[str, str]],
    ) -> dict[str, Any]:
        payload = json.loads(raw)
        valid_keys = {f["key"] for f in factors}
        by_index: dict[int, dict[str, Any]] = {}
        for item in payload.get("sentences", []):
            if not isinstance(item, dict):
                continue
            idx = int(item.get("sentence_index", -1))
            if idx < 0:
                continue
            is_consistent = bool(item.get("is_consistent", True))
            raw_violated = item.get("violated_factors", [])
            violated = [k for k in raw_violated if isinstance(k, str) and k in valid_keys] if not is_consistent else []
            reason = str(item.get("inconsistency_reason", "")).strip() or None
            rewrite = str(item.get("suggested_rewrite", "")).strip() or None

            has_implicit = bool(item.get("has_implicit_style_issue", False)) and is_consistent
            implicit_reason = str(item.get("implicit_style_reason", "")).strip() or None
            implicit_rewrite = str(item.get("implicit_style_rewrite", "")).strip() or None

            by_index[idx] = {
                "is_consistent": is_consistent,
                "violated_factors": violated,
                "inconsistency_reason": reason if not is_consistent else None,
                "suggested_rewrite": rewrite if not is_consistent else None,
                "has_implicit_style_issue": has_implicit,
                "implicit_style_reason": implicit_reason if has_implicit else None,
                "implicit_style_rewrite": implicit_rewrite if has_implicit else None,
            }

        results = []
        for s in sentences:
            matched = by_index.get(s.index, {
                "is_consistent": True,
                "violated_factors": [],
                "inconsistency_reason": None,
                "suggested_rewrite": None,
                "has_implicit_style_issue": False,
                "implicit_style_reason": None,
                "implicit_style_rewrite": None,
            })
            results.append({"sentence_index": s.index, **matched})
        return {"sentences": results, "source": "ai"}

    def _rule_based_sentences(self, sentences: list[SentenceToken], factors: list[dict[str, str]]) -> dict[str, Any]:
        from collections import Counter
        labels = [self._fallback_formality.detect_formality(s.ending) for s in sentences]
        counter: Counter[str] = Counter(labels)
        dominant = counter.most_common(1)[0][0] if counter else "중립 존댓말"
        results = []
        for s, label in zip(sentences, labels):
            ok = label == dominant
            results.append({
                "sentence_index": s.index,
                "is_consistent": ok,
                "violated_factors": [] if ok else ["formality_expected"],
                "inconsistency_reason": None if ok else f"주된 격식({dominant})과 다른 표현입니다.",
                "suggested_rewrite": None,
                "has_implicit_style_issue": False,
                "implicit_style_reason": None,
                "implicit_style_rewrite": None,
            })
        return {"sentences": results, "source": "rule-based"}

    # ── 2차: 전체 흐름 검토 ───────────────────────────────────────────────────

    def check_document_flow(
        self,
        text: str,
        context: dict[str, str],
        pass1_sentences: list[dict[str, Any]],
        factors: list[dict[str, str]],
    ) -> dict[str, Any]:
        cache_key = "flow:" + self._hash(text, [s["sentence_index"] for s in pass1_sentences])
        if cache_key in self._cache:
            return self._cache[cache_key]

        if not pass1_sentences or self._client is None:
            return self._rule_based_flow(pass1_sentences)

        prompt = self._build_flow_prompt(text, context, pass1_sentences, factors)
        last_err = "UnknownError"
        for model in self._candidate_models():
            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                    raw = ex.submit(self._call, SYSTEM_PROMPT_FLOW, model, prompt).result(
                        timeout=settings.llm_timeout_seconds
                    )
                result = self._parse_flow(raw, pass1_sentences)
                if result["sentences"]:
                    self._cache[cache_key] = result
                    return result
            except concurrent.futures.TimeoutError:
                last_err = "TimeoutError"
            except Exception as exc:  # pragma: no cover
                last_err = exc.__class__.__name__

        result = self._rule_based_flow(pass1_sentences)
        result["source"] = f"rule-based-fallback:{last_err}"
        self._cache[cache_key] = result
        return result

    def _build_flow_prompt(self, text, context, pass1_sentences, factors) -> str:
        context_lines = "\n".join(f"- {f['label']}: {context.get(f['key'], '파악 불가')}" for f in factors)
        sentence_lines = "\n".join(
            "- index={idx}, text=\"{text}\", 1차결과={result}".format(
                idx=s["sentence_index"], text=s.get("text", ""),
                result="불일치" if not s["is_consistent"] else "일치",
            )
            for s in pass1_sentences
        )
        return (
            f"[파악된 맥락]\n{context_lines}\n\n"
            f"[전체 원문]\n{text}\n\n"
            f"[문장별 1차 분석 결과]\n{sentence_lines}\n\n"
            "[지시]\n"
            "1차 분석에서 각 문장이 개별 맥락 요소와 일치하는지 확인했습니다.\n"
            "이제 글 전체의 흐름과 응집성 관점에서 2차 검토를 하세요.\n\n"
            "다음 기준으로 흐름 문제를 판단하세요:\n"
            "- 문장 간 전환이 갑작스럽거나 어색한 경우\n"
            "- 개별 요소는 맞지만 전체 메시지의 일관성을 해치는 경우\n"
            "- 주제나 논리 흐름에서 뜬금없이 벗어나는 경우\n"
            "- 전체 글의 목적과 어울리지 않는 어조나 내용인 경우\n\n"
            "- has_flow_issue=true인 문장만 flow_issue_reason과 flow_suggested_rewrite를 작성하세요.\n"
            "- flow_suggested_rewrite 작성 원칙:\n"
            "  · 흐름 문제를 일으키는 표현만 최소한으로 수정하세요.\n"
            "  · 문제없는 부분은 원문 표현을 그대로 유지하세요.\n"
            "  · 글의 말투·리듬·구체적 디테일(장소·인물·상황)을 삭제하거나 일반화하지 마세요.\n"
            "  · 이 글 특유의 결(거칠거나 투박한 표현 포함)을 살린 채 흐름만 자연스럽게 만드세요.\n"
            "  · 전환이 어색하더라도 다음 문장 내용을 가져오지 마세요.\n"
            "    현재 문장 표현·어조를 수정해서 흐름을 부드럽게 하세요.\n"
            "  · 해당 문장 하나의 내용만 포함하고, 앞뒤 문장과 합치지 마세요.\n"
            "- flow_summary에 글 전체 흐름 종합 평가를 한 문장으로 작성하세요.\n"
            "[출력 형식]\n"
            "{\n"
            '  "flow_summary": "...",\n'
            '  "sentences": [\n'
            '    { "sentence_index": 0, "has_flow_issue": false, "flow_issue_reason": "", "flow_suggested_rewrite": "" }\n'
            "  ]\n"
            "}"
        )

    def _parse_flow(self, raw: str, pass1_sentences: list[dict[str, Any]]) -> dict[str, Any]:
        payload = json.loads(raw)
        flow_summary = str(payload.get("flow_summary", "")).strip()
        by_index: dict[int, dict[str, Any]] = {}
        for item in payload.get("sentences", []):
            if not isinstance(item, dict):
                continue
            idx = int(item.get("sentence_index", -1))
            if idx < 0:
                continue
            has_issue = bool(item.get("has_flow_issue", False))
            reason = str(item.get("flow_issue_reason", "")).strip() or None
            rewrite = str(item.get("flow_suggested_rewrite", "")).strip() or None
            by_index[idx] = {
                "has_flow_issue": has_issue,
                "flow_issue_reason": reason if has_issue else None,
                "flow_suggested_rewrite": rewrite if has_issue else None,
            }
        results = []
        for s in pass1_sentences:
            idx = s["sentence_index"]
            matched = by_index.get(idx, {"has_flow_issue": False, "flow_issue_reason": None, "flow_suggested_rewrite": None})
            results.append({"sentence_index": idx, **matched})
        return {"flow_summary": flow_summary, "sentences": results, "source": "ai"}

    def _rule_based_flow(self, pass1_sentences: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "flow_summary": "흐름 분석은 AI 연결 시 제공됩니다.",
            "sentences": [{"sentence_index": s["sentence_index"], "has_flow_issue": False, "flow_issue_reason": None, "flow_suggested_rewrite": None} for s in pass1_sentences],
            "source": "rule-based",
        }

    # ── 공통 ──────────────────────────────────────────────────────────────────

    def _call(self, system: str, model: str, prompt: str) -> str:
        if self._client is None:
            return ""
        response = self._client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=3000,
        )
        return response.choices[0].message.content or ""

    def _candidate_models(self) -> list[str]:
        models = [settings.llm_model]
        models.extend(m.strip() for m in settings.llm_fallback_models.split(",") if m.strip())
        deduped: list[str] = []
        for m in models:
            if m not in deduped:
                deduped.append(m)
        return deduped

    def _hash(self, *parts: Any) -> str:
        serialized = json.dumps(parts, ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(serialized.encode()).hexdigest()
