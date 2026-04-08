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
    description: "회사, 발표, 면접, 공적인 대화에서 사용하는 딱딱한 존댓말입니다.",
    example: "자료를 검토해 주시기 바랍니다.",
  },
  "중립 존댓말": {
    title: "중립 존댓말",
    description: "일상 대화, 서비스업 등에서 사용하는 부드러운 존댓말입니다.",
    example: "자료를 확인해 주세요.",
  },
  "비격식 반말": {
    title: "비격식 반말",
    description: "친근하지만 기본적인 예의를 유지하는 반말입니다.",
    example: "자료 확인해줘.",
  },
};

const SCORE_GUIDE = [
  { title: "격식 점수", description: "문장 종결어미보다 문맥과 뉘앙스를 포함해 얼마나 일정한 격식을 유지하는지 봅니다." },
  { title: "톤", description: "부탁, 안내, 지시, 배려 같은 어조가 어떤 성격인지 분류합니다." },
  { title: "일관성 점수", description: "문장 사이에서 격식 단계가 얼마나 흔들리지 않는지 확인합니다." },
  { title: "종합 점수", description: "AI 기반 격식 분석, 일관성, 톤 신뢰도를 함께 반영한 결과입니다." },
] as const;

function isFormalityLevel(value: string): value is Exclude<FormalityLevel, "mixed"> {
  return value === "격식 존댓말" || value === "중립 존댓말" || value === "비격식 반말";
}

function getRewriteSourceLabel(source: RewriteSuggestion["source"]) {
  return source === "ai" ? "AI 제안" : "규칙 기반 보정";
}

function App() {
  const [text, setText] = useState(SAMPLE_TEXT);
  const [result, setResult] = useState<FullAnalysisResponse | null>(null);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [rewritePlan, setRewritePlan] = useState<RewritePlanResponse | null>(null);
  const [selectedLevel, setSelectedLevel] = useState<TargetRewriteLevel | null>(null);
  const [loading, setLoading] = useState(false);
  const [rewriteLoading, setRewriteLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void loadSidebarData();
  }, []);

  async function loadSidebarData() {
    try {
      const [historyItems, statsItem] = await Promise.all([fetchHistory(), fetchStats()]);
      setHistory(historyItems);
      setStats(statsItem);
    } catch {
      setError("사이드바 정보를 불러오는 중 문제가 발생했습니다.");
    }
  }

  function getAvailableLevels(analysisResult: FullAnalysisResponse): TargetRewriteLevel[] {
    const filtered = analysisResult.endings_distribution.map((item) => item.label).filter(isFormalityLevel);
    return Array.from(new Set(filtered));
  }

  async function handleAnalyze() {
    setLoading(true);
    setError(null);
    setRewritePlan(null);
    try {
      const analysisResult = await analyzeText(text);
      setResult(analysisResult);
      await loadSidebarData();
      const levels = getAvailableLevels(analysisResult);
      const defaultLevel = levels[0] ?? null;
      setSelectedLevel(defaultLevel);
      if (defaultLevel) {
        await handleRewritePlan(text, defaultLevel);
      }
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "분석 중 오류가 발생했습니다.");
    } finally {
      setLoading(false);
    }
  }

  async function handleRewritePlan(currentText: string, level: TargetRewriteLevel) {
    setRewriteLoading(true);
    setError(null);
    setSelectedLevel(level);
    try {
      const plan = await fetchRewritePlan(currentText, level);
      setRewritePlan(plan);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "수정안을 불러오지 못했습니다.");
    } finally {
      setRewriteLoading(false);
    }
  }

  const rewriteMap = useMemo(() => {
    const map = new Map<number, RewriteSuggestion>();
    rewritePlan?.rewrites.forEach((item) => map.set(item.sentence_index, item));
    return map;
  }, [rewritePlan]);

  const availableLevels = useMemo(() => (result ? getAvailableLevels(result) : []), [result]);
  const selectedGuide = selectedLevel ? FORMALITY_GUIDE[selectedLevel] : null;

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-block">
          <p className="brand-block__eyebrow">Business Korean QA</p>
          <h1>Tone Analyzer</h1>
          <p className="brand-block__description">문서의 격식을 AI가 문맥까지 보고 분석하고, 선택한 기준에 맞지 않는 문장만 골라 수정안을 제안합니다.</p>
        </div>
        <div className="stats-stack">
          <MetricCard title="전체 분석 수" value={`${stats?.total_analyses ?? 0}`} subtitle={`평균 점수 ${stats?.average_score ?? 0}`} accent="green" />
          <MetricCard title="가장 자주 나온 격식" value={stats?.most_common_formality ?? "n/a"} subtitle={`대표 톤 ${stats?.most_common_tone ?? "n/a"}`} accent="orange" />
        </div>
        <HistoryPanel items={history} />
      </aside>

      <main className="main-content">
        <section className="hero">
          <div>
            <p className="hero__kicker">Analyzer MVP</p>
            <h2>격식 구조는 이제 3단계입니다. AI가 문장의 뉘앙스를 보고 격식을 판단하고, 원하는 단계로 맞추는 수정안을 제안합니다.</h2>
          </div>
          <button className="ghost-button" type="button" onClick={() => setText(SAMPLE_TEXT)}>샘플 문장 불러오기</button>
        </section>

        <section className="workspace-grid">
          <section className="panel panel--input">
            <div className="panel__header">
              <h3>원문 입력</h3>
              <span>{text.length} / 5000자</span>
            </div>
            <textarea className="text-editor" value={text} onChange={(event) => setText(event.target.value)} placeholder="문장을 입력하거나 붙여넣어 주세요. 문장 분리는 온점(.) 기준으로 처리됩니다." />
            <div className="input-actions">
              <button className="primary-button" type="button" onClick={() => void handleAnalyze()} disabled={loading}>{loading ? "분석 중..." : "분석 실행"}</button>
            </div>
            {error ? <p className="error-text">{error}</p> : null}
          </section>

          <section className="results-grid">
            <div className="metrics-grid">
              <MetricCard title="종합 점수" value={result ? `${result.overall_score}` : "-"} subtitle={result?.summary ?? "분석을 실행하면 결과 요약이 표시됩니다."} accent="blue" />
              <MetricCard title="격식 결과" value={result && result.formality_level !== "mixed" ? FORMALITY_GUIDE[result.formality_level].title : result?.formality_level ?? "-"} subtitle={`격식 점수 ${result?.formality_score ?? "-"}`} accent="red" />
              <MetricCard title="일관성" value={result ? `${result.consistency_score}` : "-"} subtitle={`문장 수 ${result?.sentence_count ?? "-"}`} accent="green" />
              <MetricCard title="톤" value={result?.tone_label ?? "-"} subtitle={`신뢰도 ${result ? `${Math.round(result.tone_confidence * 100)}%` : "-"}`} accent="orange" />
            </div>

            <section className="panel">
              <div className="panel__header"><h3>평가 기준 안내</h3></div>
              <div className="guide-grid">
                {SCORE_GUIDE.map((item) => (
                  <article className="guide-card" key={item.title}><strong>{item.title}</strong><p>{item.description}</p></article>
                ))}
              </div>
            </section>

            <section className="panel">
              <div className="panel__header"><h3>격식 단계</h3></div>
              <div className="guide-grid">
                {Object.entries(FORMALITY_GUIDE).map(([key, item]) => (
                  <article className={`guide-card ${result?.formality_level === key ? "guide-card--active" : ""}`} key={key}><strong>{item.title}</strong><p>{item.description}</p><small>예시: {item.example}</small></article>
                ))}
              </div>
            </section>

            <section className="panel">
              <div className="panel__header"><h3>수정 기준 선택</h3></div>
              <div className="formality-selector">
                {availableLevels.map((level) => (
                  <button key={level} type="button" className={`formality-chip ${selectedLevel === level ? "is-active" : ""}`} onClick={() => void handleRewritePlan(text, level)} disabled={rewriteLoading}>
                    <strong>{FORMALITY_GUIDE[level].title}</strong>
                    <span>{level}</span>
                  </button>
                ))}
              </div>
              {selectedGuide ? <div className="selected-formality-note"><p><strong>현재 선택한 격식</strong>은 {selectedGuide.title}입니다.</p><p>{selectedGuide.description}</p><small>예시: {selectedGuide.example}</small></div> : null}
            </section>

            <DistributionChart items={result?.endings_distribution ?? []} title="격식 분포" />

            <section className="panel">
              <div className="panel__header">
                <h3>문장별 수정 제안</h3>
                <span>{rewriteLoading ? "AI가 선택한 격식 기준에 맞는 수정안을 생성하고 있습니다." : "기준에 맞지 않는 문장은 빨간색으로 표시됩니다. 마우스를 올리면 제안이 보입니다."}</span>
              </div>
              {rewritePlan ? <p className="rewrite-summary">{rewritePlan.summary}</p> : null}
              <div className="sentence-review-list">
                {!result ? <p className="empty-state">분석을 실행하면 문장별 상태와 수정안이 표시됩니다.</p> : null}
                {result?.sentences.map((sentence) => {
                  const rewrite = rewriteMap.get(sentence.index);
                  const mismatched = !!selectedLevel && sentence.formality !== selectedLevel;
                  return (
                    <div className={`sentence-review-item ${mismatched ? "is-mismatched" : ""}`} key={sentence.index}>
                      <span className="sentence-review-index">{sentence.index + 1}</span>
                      <span className="sentence-review-text">{sentence.text}</span>
                      <span className="sentence-review-badge">{sentence.formality}</span>
                      {rewrite ? <div className="sentence-tooltip"><strong>수정 이유</strong><p>{rewrite.reason}</p><strong>제안 문장</strong><p>{rewrite.suggested_sentence}</p><strong>생성 방식</strong><p>{getRewriteSourceLabel(rewrite.source)}</p></div> : null}
                    </div>
                  );
                })}
              </div>
            </section>
          </section>
        </section>
      </main>
    </div>
  );
}

export default App;