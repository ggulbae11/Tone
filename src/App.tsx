import { useEffect, useMemo, useState } from "react";
import { DistributionChart } from "./components/analysis/DistributionChart";
import { MetricCard } from "./components/common/MetricCard";
import { HistoryPanel } from "./components/dashboard/HistoryPanel";
import { analyzeText, fetchHistory, fetchRewritePlan, fetchStats } from "./services/api";
import type {
  FormalityLevel,
  FullAnalysisResponse,
  HistoryItem,
  RewritePlanResponse,
  RewriteSuggestion,
  StatsResponse,
  TargetRewriteLevel,
} from "./types/analysis";

const SAMPLE_TEXT = "안녕하세요. 이번 주 보고서는 내일까지 보내줘. 세부 수치는 제가 다시 확인해보겠습니다. 필요하면 바로 수정할게.";

const FORMALITY_GUIDE: Record<Exclude<FormalityLevel, "mixed">, { title: string; description: string; example: string }> = {
  "격식 존댓말": {
    title: "격식 존댓말",
    description: "회사·공적 문서·발표용",
    example: "자료를 검토해 주시기 바랍니다.",
  },
  "중립 존댓말": {
    title: "중립 존댓말",
    description: "일상 업무·부드러운 존댓말",
    example: "자료를 확인해 주세요.",
  },
  "비격식 반말": {
    title: "비격식 반말",
    description: "친근한 대화·가벼운 표현",
    example: "자료 확인해줘.",
  },
};

const AVAILABLE_LEVELS: TargetRewriteLevel[] = ["비격식 반말", "중립 존댓말", "격식 존댓말"];
{/*function isFormalityLevel(value: string): value is Exclude<FormalityLevel, "mixed"> {
  return value === "격식 존댓말" || value === "중립 존댓말" || value === "비격식 반말";
}*/}
const items: HistoryItem[] = [];
function getRewriteSourceLabel(source: RewriteSuggestion["source"]) {
  return source === "ai" ? "AI 제안" : "규칙 기반 보정";
}

function getErrorMessage(error: unknown, fallback: string) {
  if (error instanceof Error) {
    if (error.message.includes("Network")) {
      return "네트워크 연결을 확인해 주세요.";
    }

    return error.message;
  }

  return fallback;
}

function App() {
  const [text, setText] = useState(SAMPLE_TEXT);
  const [result, setResult] = useState<FullAnalysisResponse | null>(null);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [rewritePlan, setRewritePlan] = useState<RewritePlanResponse | null>(null);
  const [selectedLevel, setSelectedLevel] = useState<Exclude<FormalityLevel, "mixed"> | "">("");
  const [selectedSentence, setSelectedSentence] = useState<number | null>(null);
  const [issueCount, setIssueCount] = useState(0);
  type LoadingState = "idle" | "analyzing" | "rewriting" | "loadingSidebar";
  const [loading, setLoading] = useState<LoadingState>("idle");

  const handleSelectHistory = async (item: HistoryItem) => {

  
  setText(item.input_text);
  setSelectedSentence(null);

  setSelectedLevel(
    item.formality_level === "mixed" ? "" : item.formality_level
  );

  setIssueCount(item.issue_count);
  setLoading("idle");
  const analysis = await analyzeText(item.input_text);
  setResult(analysis);
  const plan = await fetchRewritePlan(
    item.input_text,
    item.formality_level === "mixed"
      ? "비격식 반말"
      : item.formality_level
  );

  setRewritePlan(plan);

};
  
    
  const [error, setError] = useState<{
    analyze?: string; rewrite?: string; sidebar?: string;
  }>({});

  useEffect(() => {
    void loadSidebarData();
  }, []);

  async function loadSidebarData() {
    try {
      const [historyItems, statsItem] = await Promise.all([fetchHistory(), fetchStats()]);
      setHistory(historyItems.slice(0, 30));
      setStats(statsItem);
    } catch {
      setError((prev) => ({...prev, sidebar: "사이드바 정보를 불러오는 중 문제가 발생했습니다.",}));
    }
  }

  async function handleAnalyze() {
    if (loading !== "idle") return;
    if (!text.trim()) {
      setError({ analyze: "분석할 문장을 입력해 주세요.", }); return; }
    if (text.length > 5000) {
      setError({ analyze: "입력은 5000자 이하만 가능합니다.", }); return; }

    setLoading("analyzing");
    setError({});

    try {
      const analysisResult = await analyzeText(text);
      setResult(analysisResult);
      await loadSidebarData();
      const defaultLevel = AVAILABLE_LEVELS[0] ?? null;
      setSelectedLevel(defaultLevel);
      if (defaultLevel) {
        setLoading("rewriting");
        const plan = await fetchRewritePlan(text, defaultLevel);
        setRewritePlan(plan);
      }
    } catch (caughtError) {
      setError((prev) => ({...prev, analyze: getErrorMessage(caughtError, "분석 중 오류가 발생했습니다."),}));
    } finally {
      setLoading("idle");
    }
  }

  async function handleRewritePlan(currentText: string, level: TargetRewriteLevel) {
    setLoading("rewriting");
    setError({});
    setSelectedLevel(level);
    setSelectedSentence(null);

    try {
      const plan = await fetchRewritePlan(currentText, level);
      setRewritePlan(plan);
    } catch (caughtError) {
      setError((prev) => ({...prev, rewrite: getErrorMessage(caughtError, "수정안을 불러오지 못했습니다."),}));
    } finally {
      setLoading("idle");
    }
  }

  const rewriteMap = useMemo(() => {
    const rewrites = rewritePlan?.rewrites ?? [];
    return new Map( rewrites.map((item) => [ item.sentence_index, item, ]) );
  }, [rewritePlan]);

  const availableLevels = AVAILABLE_LEVELS;
  const selectedGuide = selectedLevel ? FORMALITY_GUIDE[selectedLevel] : null;
  const filteredSentences = result?.sentences ?? [];
  const selectedRewrite = selectedSentence !== null ? rewriteMap.get(selectedSentence) : null;
  const selectedSentenceData = selectedSentence !== null ? filteredSentences.find( (sentence) => sentence.index === selectedSentence ) : null;
  const summaryText = rewritePlan && rewritePlan.rewrites.length > 0 ? `${rewritePlan.rewrites.length}개의 문장을 수정했습니다.` : null;

  
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-block">
          <p className="brand-block__eyebrow">Business Korean QA</p>
          <h1>Tone Analyzer</h1>
          <p className="brand-block__description">문서의 격식을 AI가 문맥까지 보고 분석하여, 선택한 기준에 맞지 않는 문장을 골라 수정안을 제시합니다.</p>
        </div>
        <div className="stats-stack">
          <MetricCard title="전체 분석 수" value={`${stats?.total_analyses ?? 0}`} subtitle={`평균 점수 ${stats?.average_score ?? 0}`} accent="green" />
          {/*<MetricCard title="가장 자주 나온 격식" value={stats?.most_common_formality ?? "n/a"} subtitle={`대표 톤 ${stats?.most_common_tone ?? "n/a"}`} accent="orange" />*/}
        </div>
        <HistoryPanel items={history} onSelect={handleSelectHistory} />
        {error.sidebar && ( <p className="error-text">{error.sidebar}</p> )}
      </aside>

      <main className="main-content">
        <section className="hero">
          <div>
            <p className="hero__kicker">Analyzer MVP</p>
            <h2>AI가 문장을 분석하고, 선택한 격식에 맞는 수정안을 제안합니다.</h2>
          </div>
          <div className="hero-actions">
            <button className="ghost-button" type="button" onClick={() => setText(SAMPLE_TEXT)}>샘플 문장</button>
            <button className="text-button" type="button" onClick={() => setText("")}>문장 지우기</button>
          </div>
        </section>

        <section className="workspace-grid">
          <section className="panel panel--input">
            
            <div className="panel__header">
              <h3>원문 입력</h3>
              <span>{text.length} / 5000자</span>
            </div>
            <textarea className="text-editor" value={text} onChange={(event) => setText(event.target.value)} placeholder="문장을 입력하거나 붙여넣어 주세요. 문장 분리는 온점(.) 기준으로 처리됩니다." />
            <div className="input-actions">
              <button className="primary-button" type="button" onClick={() => void handleAnalyze()} disabled={loading !== "idle" || !text.trim()}>{loading === "analyzing" ? "분석 중..." : "분석 실행"}</button>
              {error.analyze && ( <p className="error-text">{error.analyze}</p> )}
            </div>
            {selectedGuide ? ( <div className="selected-formality-note"><strong>{selectedGuide.title}</strong> <p>{selectedGuide.description}</p><small>예: {selectedGuide.example}</small></div> ) : null}
          </section>

          <section className="results-grid">
            
            <div className="metrics-grid">
              <MetricCard title="종합 점수" value={result ? `${result.overall_score}` : "-"} subtitle={result?.summary ?? "분석을 실행하면 결과 요약이 표시됩니다."} accent="blue" />
              <MetricCard title="격식 결과" value={result && result.formality_level !== "mixed" ? FORMALITY_GUIDE[result.formality_level].title : result?.formality_level ?? "-"} subtitle={`격식 점수 ${result?.formality_score ?? "-"}`} accent="red" />
              <MetricCard title="일관성" value={result ? `${result.consistency_score}` : "-"} subtitle={`문장 수 ${result?.sentence_count ?? "-"}`} accent="green" />
              <MetricCard title="톤" value={result?.tone_label ?? "-"} subtitle={`신뢰도 ${result ? `${Math.round(result.tone_confidence * 100)}%` : "-"}`} accent="orange" />
            </div>

            <DistributionChart items={result?.endings_distribution ?? []} title="격식 분포" />

            <section className="panel">
              <div className="panel__header"><h3>수정 기준 선택</h3></div>
              <div className="formality-selector">
                {availableLevels.map((level) => (
                  <button key={level} type="button" className={`formality-chip ${selectedLevel === level ? "is-active" : ""}`} onClick={() => void handleRewritePlan(text, level)} disabled={loading !== "idle"}>
                    <span>{FORMALITY_GUIDE[level].title}</span>
                  </button>
                ))}
              </div>
            </section>
            
            <section className="panel">
              <div className="panel__header">
                <span className="rewrite-status">
                  {loading === "rewriting" ? `${selectedLevel}을 기준으로 분석 중입니다...` : rewritePlan ? `${selectedLevel}을 기준으로 수정 완료` : "" }
                </span>
              </div>
              {summaryText && loading !== "rewriting" ? ( <p className="rewrite-summary">{summaryText}</p> ) : null}
              {selectedRewrite && selectedSentenceData ? (
                <div className="rewrite-detail-panel">
                  <h4 className="rewrite-detail-title"> 수정 제안 상세 </h4>
                  <div className="tooltip-section"> <span className="tooltip-label">수정 이유</span> <p>{selectedRewrite.reason}</p> </div>
                  <div className="tooltip-section"> <span className="tooltip-label">원문</span> <p>{selectedSentenceData.text}</p> </div>
                  <div className="tooltip-section tooltip-section--highlight"> <span className="tooltip-label">제안 문장</span> <p>{selectedRewrite.suggested_sentence}</p> </div>
                  <div className="tooltip-footer"> {getRewriteSourceLabel(selectedRewrite.source)} </div>
                </div>
              ) : null}
              <div className="sentence-review-list">
                {loading === "rewriting" ? (
                  <div className="analysis-loading">
                    <div className="loading-title"> 문장을 분석하고 있습니다... </div>
                    <div className="sentence-skeleton-list">
                      <div className="sentence-skeleton" />
                      <div className="sentence-skeleton" />
                      <div className="sentence-skeleton" />
                    </div>
                  </div>
                ) : !rewritePlan ? (
                  <p className="empty-state"> 분석을 실행하면 AI 수정안이 표시됩니다. </p>
                ) : rewriteMap.size === 0 ? (
                  <p className="empty-state"> 선택한 격식 기준에서 수정이 필요한 문장이 없습니다. </p>
                ) : ( 
                  filteredSentences.map((sentence) => {
                    const mismatched = selectedLevel !== null && sentence.formality !== selectedLevel;
                    const hasRewrite = rewriteMap.has(sentence.index);
                    return (
                      <div className={`sentence-review-item ${mismatched ? "is-mismatched" : ""} ${selectedSentence === sentence.index ? "is-selected" : ""} ${hasRewrite ? "has-rewrite" : ""}`} key={sentence.index} onClick={() => { if (!hasRewrite) return; setSelectedSentence((prev) => prev === sentence.index ? null : sentence.index ); }}>
                        <span className="sentence-review-index">{sentence.index + 1}</span>
                        <span className="sentence-review-text">{sentence.text}</span>
                        <span className="sentence-review-badge">{sentence.formality}</span>
                      </div>
                    );
                  })
                )}
              </div>
              
            </section>
          </section>
        </section>
      </main>
    </div>
  );
}

export default App;