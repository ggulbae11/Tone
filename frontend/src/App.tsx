import { useEffect, useRef, useState } from "react";
import { ContextEditor } from "./components/analysis/ContextEditor";
import { ContextPanel } from "./components/analysis/ContextPanel";
import { MetricCard } from "./components/common/MetricCard";
import { HistoryPanel } from "./components/dashboard/HistoryPanel";
import { analyzeSentences, clearHistory, extractContext, fetchHistory, fetchStats } from "./services/api";
import type {
  ContextAnalysis,
  FullAnalysisResponse,
  HistoryItem,
  SentenceResult,
  StatsResponse,
} from "./types/analysis";

const SAMPLE_TEXT =
  "안녕하세요. 이번 주 보고서는 내일까지 보내줘. 세부 수치는 제가 다시 확인해보겠습니다. 필요하면 바로 수정할게.";

type Step = "input" | "context-review" | "results";

function getSentenceState(s: SentenceResult): "bad" | "flow" | "style" | "ok" {
  if (!s.is_consistent) return "bad";
  if (s.has_flow_issue) return "flow";
  if (s.has_implicit_style_issue) return "style";
  return "ok";
}

export default function App() {
  const [step, setStep] = useState<Step>("input");
  const [text, setText] = useState(SAMPLE_TEXT);

  // 1단계 결과 — 편집 가능한 맥락 draft
  const [contextDraft, setContextDraft] = useState<ContextAnalysis | null>(null);

  // 2단계 결과
  const [result, setResult] = useState<FullAnalysisResponse | null>(null);

  // 수정 적용 상태: sentenceIndex → 적용된 수정 텍스트
  const [appliedRewrites, setAppliedRewrites] = useState<Map<number, string>>(new Map());

  // 복사 피드백
  const [copyFeedback, setCopyFeedback] = useState(false);

  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [openIndex, setOpenIndex] = useState<number | null>(null);
  const [loadingCtx, setLoadingCtx] = useState(false);
  const [loadingSent, setLoadingSent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const mainRef = useRef<HTMLElement>(null);

  useEffect(() => { void loadSidebarData(); }, []);
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (!(e.target instanceof HTMLElement) || !e.target.closest(".sentence-item")) {
        setOpenIndex(null);
      }
    }
    document.addEventListener("click", handleClick);
    return () => document.removeEventListener("click", handleClick);
  }, []);

  async function loadSidebarData() {
    try {
      const [h, s] = await Promise.all([fetchHistory(), fetchStats()]);
      setHistory(h);
      setStats(s);
    } catch { /* 사이드바 오류 무시 */ }
  }

  // ── 1단계: 맥락 추출 ───────────────────────────────────────────────────────
  async function handleExtractContext() {
    setLoadingCtx(true);
    setError(null);
    try {
      const res = await extractContext(text);
      setContextDraft(res.context);
      setResult(null);
      setStep("context-review");
    } catch (err) {
      setError(err instanceof Error ? err.message : "맥락 추출 중 오류가 발생했습니다.");
    } finally {
      setLoadingCtx(false);
    }
  }

  // ── 2단계: 문장 분석 ───────────────────────────────────────────────────────
  async function handleAnalyzeSentences() {
    if (!contextDraft) return;
    setLoadingSent(true);
    setError(null);
    setOpenIndex(null);
    try {
      const contextValues = Object.fromEntries(contextDraft.factors.map((f) => [f.key, f.value]));
      const implicitStyleValue = contextDraft.implicit_style?.value ?? "";
      const res = await analyzeSentences(
        text,
        contextValues,
        contextDraft.overall_summary,
        implicitStyleValue,
      );
      setResult(res);
      setAppliedRewrites(new Map());
      setCopyFeedback(false);
      setStep("results");
      await loadSidebarData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "문장 분석 중 오류가 발생했습니다.");
    } finally {
      setLoadingSent(false);
    }
  }

  // ── 수정 적용 토글 ─────────────────────────────────────────────────────────
  function toggleApply(sentenceIndex: number, rewriteText: string) {
    setAppliedRewrites((prev) => {
      const next = new Map(prev);
      if (next.get(sentenceIndex) === rewriteText) {
        next.delete(sentenceIndex);
      } else {
        next.set(sentenceIndex, rewriteText);
      }
      return next;
    });
  }

  // ── 수정된 전체글 조합 ─────────────────────────────────────────────────────
  function getRevisedText(): string {
    if (!result) return "";
    return [...result.sentences]
      .sort((a, b) => a.index - b.index)
      .map((s) => (appliedRewrites.get(s.index) ?? s.text).trim())
      .join(" ");
  }

  async function handleCopyRevised() {
    try {
      await navigator.clipboard.writeText(getRevisedText());
      setCopyFeedback(true);
      setTimeout(() => setCopyFeedback(false), 2000);
    } catch {
      setError("클립보드 복사에 실패했습니다.");
    }
  }

  // ── 맥락 편집 핸들러 ──────────────────────────────────────────────────────
  function handleFactorChange(key: string, value: string) {
    setContextDraft((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        factors: prev.factors.map((f) => (f.key === key ? { ...f, value } : f)),
      };
    });
  }

  function handleSummaryChange(summary: string) {
    setContextDraft((prev) => (prev ? { ...prev, overall_summary: summary } : prev));
  }

  function handleImplicitStyleChange(value: string) {
    setContextDraft((prev) => {
      if (!prev) return prev;
      if (!value.trim()) {
        return { ...prev, implicit_style: null };
      }
      return {
        ...prev,
        implicit_style: prev.implicit_style
          ? { ...prev.implicit_style, value }
          : { value, reason: "" },
      };
    });
  }

  async function handleClearHistory() {
    try { await clearHistory(); await loadSidebarData(); }
    catch { setError("이력 삭제 중 오류가 발생했습니다."); }
  }

  function handleSelectHistory(item: HistoryItem) {
    setText(item.input_text);
    setResult(item.result_payload);
    setContextDraft(item.result_payload.context);
    setAppliedRewrites(new Map());
    setCopyFeedback(false);
    setStep("results");
    setOpenIndex(null);
    setError(null);
    mainRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  const scoreColor = result
    ? result.overall_score >= 80 ? "green" : result.overall_score >= 50 ? "orange" : "red"
    : "blue";

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-block">
          <p className="brand-block__eyebrow">Korean Tone</p>
          <h1>Tone Analyzer</h1>
          <p className="brand-block__description">
            글의 맥락을 파악하고, 각 문장이 전체 흐름과 일치하는지 2단계로 분석합니다.
          </p>
        </div>
        <div className="stats-stack">
          <MetricCard title="전체 분석 수" value={`${stats?.total_analyses ?? 0}`}
            subtitle={`평균 일치도 ${stats?.average_score ?? 0}점`} accent="green" />
          <MetricCard title="가장 자주 나온 격식" value={stats?.most_common_formality ?? "n/a"}
            subtitle="누적 분석 데이터" accent="orange" />
        </div>
        <HistoryPanel items={history} onClear={() => void handleClearHistory()} onSelect={handleSelectHistory} />
      </aside>

      <main className="main-content" ref={mainRef}>

        {/* ── 진행 단계 표시 ── */}
        <div className="step-indicator">
          <div className={`step-indicator__item ${step === "input" ? "is-active" : "is-done"}`}>
            <span className="step-indicator__num">1</span>
            <span>원문 입력 · 맥락 추출</span>
          </div>
          <div className="step-indicator__line" />
          <div className={`step-indicator__item ${step === "context-review" ? "is-active" : step === "results" ? "is-done" : ""}`}>
            <span className="step-indicator__num">2</span>
            <span>맥락 검토 · 수정</span>
          </div>
          <div className="step-indicator__line" />
          <div className={`step-indicator__item ${step === "results" ? "is-active" : ""}`}>
            <span className="step-indicator__num">3</span>
            <span>문장 분석 결과</span>
          </div>
        </div>

        {error ? <p className="error-text error-text--top">{error}</p> : null}

        {/* ════════════════════════════════════════════
            STEP 1: 원문 입력
        ════════════════════════════════════════════ */}
        {step === "input" && (
          <section className="workspace-grid">
            <section className="panel panel--input">
              <div className="panel__header">
                <h3>원문 입력</h3>
                <span>{text.length} / 5000자</span>
              </div>
              <textarea
                className="text-editor"
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="문장을 입력하거나 붙여넣어 주세요. 마침표(.)를 기준으로 문장을 나눕니다."
              />
              <div className="input-actions">
                <button className="ghost-button" type="button" onClick={() => setText(SAMPLE_TEXT)}>
                  샘플 불러오기
                </button>
                <button className="primary-button" type="button"
                  onClick={() => void handleExtractContext()} disabled={loadingCtx || !text.trim()}>
                  {loadingCtx ? "맥락 추출 중..." : "맥락 분석 →"}
                </button>
              </div>
            </section>
            <div className="step-guide panel">
              <p className="step-guide__kicker">분석 흐름</p>
              <ol className="step-guide__list">
                <li><strong>맥락 분석</strong> — AI가 상황·관계·격식 등을 추론합니다.</li>
                <li><strong>맥락 검토</strong> — 추론 결과를 직접 확인하고 수정합니다.</li>
                <li><strong>문장 분석</strong> — 확정된 맥락 기준으로 각 문장을 검토합니다.</li>
              </ol>
            </div>
          </section>
        )}

        {/* ════════════════════════════════════════════
            STEP 2: 맥락 검토 · 수정
        ════════════════════════════════════════════ */}
        {step === "context-review" && contextDraft && (
          <section className="workspace-grid">
            <div className="input-column">
              <section className="panel">
                <div className="panel__header">
                  <h3>입력된 원문</h3>
                  <button className="ghost-button ghost-button--sm" type="button"
                    onClick={() => setStep("input")}>
                    ← 수정
                  </button>
                </div>
                <p className="text-preview">{text}</p>
              </section>
            </div>

            <div className="results-column">
              <ContextEditor
                context={contextDraft}
                onFactorChange={handleFactorChange}
                onSummaryChange={handleSummaryChange}
                onImplicitStyleChange={handleImplicitStyleChange}
              />
              <div className="step2-actions">
                <button className="primary-button" type="button"
                  onClick={() => void handleAnalyzeSentences()} disabled={loadingSent}>
                  {loadingSent ? "문장 분석 중..." : "문장 분석 실행 →"}
                </button>
              </div>
            </div>
          </section>
        )}

        {/* ════════════════════════════════════════════
            STEP 3: 분석 결과
        ════════════════════════════════════════════ */}
        {step === "results" && result && (
          <section className="workspace-grid">
            <div className="input-column">
              <ContextPanel context={result.context} />
              {result.flow_summary ? (
                <section className="panel flow-summary-panel">
                  <div className="panel__header">
                    <h3>전체 흐름 평가</h3>
                    <span className="badge badge--blue">2차 분석</span>
                  </div>
                  <p className="flow-summary-text">{result.flow_summary}</p>
                </section>
              ) : null}
              <div className="results-back-actions">
                <button className="ghost-button" type="button"
                  onClick={() => { setStep("context-review"); setResult(null); }}>
                  ← 맥락 수정
                </button>
                <button className="ghost-button" type="button"
                  onClick={() => { setStep("input"); setResult(null); setContextDraft(null); }}>
                  ← 처음부터
                </button>
              </div>
            </div>

            <div className="results-column">
              <div className="metrics-row">
                <MetricCard title="맥락 일치도" value={`${result.overall_score}점`}
                  subtitle={result.summary} accent={scoreColor} />
                <MetricCard title="문장 현황"
                  value={`${result.consistent_count} / ${result.sentences.length}`}
                  subtitle={`불일치 ${result.inconsistent_count} · 흐름 ${result.flow_issue_count} · 문체 ${result.implicit_style_issue_count}`}
                  accent="blue" />
              </div>

              {/* ── 문장별 분석 ── */}
              <section className="panel">
                <div className="panel__header">
                  <h3>문장별 분석</h3>
                  <div className="legend">
                    <span className="legend-item legend-item--bad">맥락 불일치</span>
                    <span className="legend-item legend-item--flow">흐름 문제</span>
                    <span className="legend-item legend-item--style">문체 이탈</span>
                  </div>
                </div>
                <div className="sentence-list">
                  {result.sentences.map((sentence) => {
                    const state = getSentenceState(sentence);
                    const isOpen = openIndex === sentence.index;
                    const isApplied = appliedRewrites.has(sentence.index);
                    return (
                      <button key={sentence.index} type="button"
                        className={`sentence-item sentence-item--${state}${isOpen ? " sentence-item--open" : ""}${isApplied ? " sentence-item--applied" : ""}`}
                        onClick={(e) => {
                          e.stopPropagation();
                          if (state !== "ok") setOpenIndex((cur) => (cur === sentence.index ? null : sentence.index));
                        }}>
                        <span className="sentence-item__num">{sentence.index + 1}</span>
                        <span className="sentence-item__text">{sentence.text}</span>
                        <div className="sentence-item__badges">
                          <span className={`sentence-item__badge sentence-item__badge--${state}`}>
                            {state === "bad" ? "맥락 불일치" : state === "flow" ? "흐름 문제" : state === "style" ? "문체 이탈" : "일치"}
                          </span>
                          {isApplied && (
                            <span className="sentence-item__badge sentence-item__badge--applied">✓ 적용됨</span>
                          )}
                        </div>

                        {state !== "ok" && isOpen && (
                          <div className="sentence-popup" onClick={(e) => e.stopPropagation()}>

                            {/* ── 1차: 맥락 불일치 ── */}
                            {!sentence.is_consistent && (<>
                              {sentence.violated_factors.length > 0 && (<>
                                <strong>위반된 요소</strong>
                                <div className="sentence-popup__tags">
                                  {sentence.violated_factors.map((key) => {
                                    const factor = result.context.factors.find((f) => f.key === key);
                                    return <span key={key} className="violated-tag">{factor?.label ?? key}</span>;
                                  })}
                                </div>
                              </>)}
                              {sentence.inconsistency_reason && (<>
                                <strong>불일치 이유</strong>
                                <p>{sentence.inconsistency_reason}</p>
                              </>)}
                              {sentence.suggested_rewrite && (
                                <div className="sentence-popup__rewrite-block">
                                  <strong>수정 제안 (1차)</strong>
                                  <p className="sentence-popup__rewrite">{sentence.suggested_rewrite}</p>
                                  <button
                                    type="button"
                                    className={`apply-btn ${appliedRewrites.get(sentence.index) === sentence.suggested_rewrite ? "apply-btn--on" : ""}`}
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      toggleApply(sentence.index, sentence.suggested_rewrite!);
                                    }}
                                  >
                                    {appliedRewrites.get(sentence.index) === sentence.suggested_rewrite ? "✓ 적용됨 — 취소" : "적용"}
                                  </button>
                                </div>
                              )}
                            </>)}

                            {/* ── 2차: 흐름 문제 ── */}
                            {sentence.has_flow_issue && (<>
                              {sentence.flow_issue_reason && (<>
                                <strong>흐름 문제</strong>
                                <p>{sentence.flow_issue_reason}</p>
                              </>)}
                              {sentence.flow_suggested_rewrite && (
                                <div className="sentence-popup__rewrite-block">
                                  <strong>수정 제안 (2차)</strong>
                                  <p className="sentence-popup__rewrite">{sentence.flow_suggested_rewrite}</p>
                                  <button
                                    type="button"
                                    className={`apply-btn ${appliedRewrites.get(sentence.index) === sentence.flow_suggested_rewrite ? "apply-btn--on" : ""}`}
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      toggleApply(sentence.index, sentence.flow_suggested_rewrite!);
                                    }}
                                  >
                                    {appliedRewrites.get(sentence.index) === sentence.flow_suggested_rewrite ? "✓ 적용됨 — 취소" : "적용"}
                                  </button>
                                </div>
                              )}
                            </>)}

                            {/* ── 3차: 암묵적 문체 이탈 ── */}
                            {sentence.has_implicit_style_issue && (<>
                              {sentence.implicit_style_reason && (<>
                                <strong>문체 이탈</strong>
                                <p>{sentence.implicit_style_reason}</p>
                              </>)}
                              {sentence.implicit_style_rewrite && (
                                <div className="sentence-popup__rewrite-block">
                                  <strong>수정 제안 (문체)</strong>
                                  <p className="sentence-popup__rewrite">{sentence.implicit_style_rewrite}</p>
                                  <button
                                    type="button"
                                    className={`apply-btn ${appliedRewrites.get(sentence.index) === sentence.implicit_style_rewrite ? "apply-btn--on" : ""}`}
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      toggleApply(sentence.index, sentence.implicit_style_rewrite!);
                                    }}
                                  >
                                    {appliedRewrites.get(sentence.index) === sentence.implicit_style_rewrite ? "✓ 적용됨 — 취소" : "적용"}
                                  </button>
                                </div>
                              )}
                            </>)}

                          </div>
                        )}
                      </button>
                    );
                  })}
                </div>
              </section>

              {/* ── 수정된 전체글 ── */}
              <section className="panel revised-panel">
                <div className="panel__header">
                  <h3>수정된 전체글</h3>
                  <div className="revised-panel__actions">
                    {appliedRewrites.size > 0 && (
                      <span className="badge badge--blue">{appliedRewrites.size}개 수정 적용됨</span>
                    )}
                    <button
                      type="button"
                      className={`ghost-button ghost-button--sm${copyFeedback ? " ghost-button--copied" : ""}`}
                      onClick={() => void handleCopyRevised()}
                    >
                      {copyFeedback ? "✓ 복사됨!" : "클립보드에 복사"}
                    </button>
                  </div>
                </div>
                <div className="revised-body">
                  {[...result.sentences]
                    .sort((a, b) => a.index - b.index)
                    .map((s) => {
                      const applied = appliedRewrites.get(s.index);
                      return (
                        <span
                          key={s.index}
                          className={`revised-sentence${applied ? " revised-sentence--applied" : ""}`}
                        >
                          {applied ?? s.text}{" "}
                        </span>
                      );
                    })}
                </div>
                {appliedRewrites.size === 0 && (
                  <p className="revised-panel__hint">
                    문장별 분석에서 수정 제안의 <strong>적용</strong> 버튼을 누르면 해당 문장이 여기서 바뀝니다.
                  </p>
                )}
              </section>

            </div>
          </section>
        )}

      </main>
    </div>
  );
}
