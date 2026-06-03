import type { ContextAnalysis } from "../../types/analysis";
import { groupFactors } from "../../utils/groupFactors";

interface ContextEditorProps {
  context: ContextAnalysis;
  onFactorChange: (key: string, value: string) => void;
  onSummaryChange: (summary: string) => void;
  onImplicitStyleChange: (value: string) => void;
}

export function ContextEditor({
  context,
  onFactorChange,
  onSummaryChange,
  onImplicitStyleChange,
}: ContextEditorProps) {
  const groups = groupFactors(context.factors);

  return (
    <section className="panel context-editor">
      <div className="panel__header">
        <h3>맥락 요소 확인 및 수정</h3>
        <span className="badge badge--blue">1단계 완료</span>
      </div>
      <p className="context-editor__desc">
        AI가 추론한 값을 검토하고 잘못된 항목은 직접 수정하세요. 수정 후 문장 분석을 실행합니다.
      </p>

      <div className="context-editor__summary-block">
        <label className="context-editor__label" htmlFor="summary-input">전체 맥락 요약</label>
        <textarea
          id="summary-input"
          className="context-editor__summary-input"
          value={context.overall_summary}
          onChange={(e) => onSummaryChange(e.target.value)}
          rows={2}
        />
      </div>

      <div className="context-editor__groups">
        {groups.map(({ group, items }) => (
          <div className="factor-group" key={group}>
            <div className="factor-group__header">
              <span className="factor-group__label">{group}</span>
              <span className="factor-group__count">{items.length}개 항목</span>
            </div>
            <div className="factor-group__items">
              {items.map((factor) => (
                <div className="context-editor__factor" key={factor.key}>
                  <div className="context-editor__factor-meta">
                    <span className="context-editor__factor-label">{factor.label}</span>
                    <span className="context-editor__factor-key">{factor.key}</span>
                  </div>
                  <input
                    className="context-editor__input"
                    type="text"
                    value={factor.value}
                    onChange={(e) => onFactorChange(factor.key, e.target.value)}
                    placeholder="값을 입력하세요"
                  />
                  <p className="context-editor__factor-desc">{factor.description}</p>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* ── 암묵적 문체 특성 ── */}
      <div className="implicit-style-block">
        <div className="implicit-style-block__header">
          <div className="implicit-style-block__title-row">
            <span className="context-editor__label">암묵적 문체 특성</span>
            {context.implicit_style
              ? <span className="badge badge--purple">AI 추출됨</span>
              : <span className="badge">해당 없음</span>
            }
          </div>
          <p className="implicit-style-block__desc">
            명시적 요소로 설명되지 않는 이 글의 고유한 문체 패턴입니다.
            비워두면 문장 분석에서 제외됩니다.
          </p>
        </div>

        {context.implicit_style?.reason && (
          <div className="implicit-style-block__reason">
            <span className="implicit-style-block__reason-label">추출 근거</span>
            <p>{context.implicit_style.reason}</p>
          </div>
        )}

        <textarea
          className="implicit-style-block__input"
          value={context.implicit_style?.value ?? ""}
          onChange={(e) => onImplicitStyleChange(e.target.value)}
          placeholder={"예: ~야/~해 어미 일관 사용, 감정 직접 표현 없음, 단문 선호\nAI가 추출하지 않은 경우 직접 입력할 수 있습니다."}
          rows={3}
        />
      </div>
    </section>
  );
}
