interface MetricCardProps {
  title: string;
  value: string;
  subtitle: string;
  accent?: "red" | "orange" | "blue" | "green";
}
const INFO_MESSAGES: Record<string, string> = {
  "종합 점수": "AI 기반 격식 분석, 일관성, 톤 신뢰도를 함께 반영한 결과입니다.",
  "격식 결과": "문장 종결어미보다 문맥과 뉘앙스를 포함해 얼마나 일정한 격식을 유지하는지 봅니다.",
  "일관성": "문장 사이에서 격식 단계가 얼마나 흔들리지 않는지 확인합니다.",
  "톤": "부탁, 안내, 지시, 배려 같은 어조가 어떤 성격인지 분류합니다.",
};
export function MetricCard({ title, value, subtitle, accent = "blue" }: MetricCardProps) {
  return (
    <article className={`metric-card metric-card--${accent}`}>
      <div className="metric-card__title-row">
        <p className="metric-card__title">{title}</p>

        {INFO_MESSAGES[title] && (
          <button className="info-button">
            ⓘ
            <span className="info-tooltip">
              {INFO_MESSAGES[title]}
            </span>
          </button>
        )}
      </div>
      <strong className="metric-card__value">{value}</strong>
      <p className="metric-card__subtitle">{subtitle}</p>
    </article>
  );
}
