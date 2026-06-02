import type { ContextAnalysis } from "../../types/analysis";
import { groupFactors } from "../../utils/groupFactors";

interface ContextPanelProps {
  context: ContextAnalysis;
}

export function ContextPanel({ context }: ContextPanelProps) {
  const jsonObject = Object.fromEntries(context.factors.map((f) => [f.key, f.value]));
  const groups = groupFactors(context.factors);

  return (
    <section className="panel context-panel">
      <div className="panel__header">
        <h3>맥락 분석</h3>
        <span className="badge badge--blue">확정됨</span>
      </div>
      <p className="context-summary">{context.overall_summary}</p>
      <div className="context-editor__groups">
        {groups.map(({ group, items }) => (
          <div className="factor-group" key={group}>
            <div className="factor-group__header">
              <span className="factor-group__label">{group}</span>
              <span className="factor-group__count">{items.length}개 항목</span>
            </div>
            <div className="factor-group__items">
              {items.map((factor) => (
                <div className="context-factor" key={factor.key}>
                  <div className="context-factor__meta">
                    <span className="context-factor__label">{factor.label}</span>
                    <span className="context-factor__key">{factor.key}</span>
                  </div>
                  <span className="context-factor__value">{factor.value}</span>
                  <p className="context-factor__desc">{factor.description}</p>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
      {/* ── 암묵적 문체 특성 ── */}
      {context.implicit_style && (
        <div className="implicit-style-result">
          <div className="implicit-style-result__header">
            <span className="context-editor__label">암묵적 문체 특성</span>
            <span className="badge badge--purple">적용됨</span>
          </div>
          <p className="implicit-style-result__value">{context.implicit_style.value}</p>
          {context.implicit_style.reason && (
            <p className="implicit-style-result__reason">{context.implicit_style.reason}</p>
          )}
        </div>
      )}

      <details className="context-json-block">
        <summary>JSON 원본 보기</summary>
        <pre className="context-json-pre">{JSON.stringify(jsonObject, null, 2)}</pre>
      </details>
    </section>
  );
}
