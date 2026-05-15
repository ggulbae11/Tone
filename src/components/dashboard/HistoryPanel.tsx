import type { HistoryItem } from "../../types/analysis";

interface HistoryPanelProps {
  items: HistoryItem[];
}

export function HistoryPanel({ items }: HistoryPanelProps) {
  return (
    <section className="panel">
      <div className="panel__header">
        <h3>최근 분석 이력</h3>
      </div>
      <div className="history-list">
        {items.length === 0 ? (
          <p className="empty-state">아직 저장된 분석 이력이 없습니다.</p>
        ) : (
          items.map((item) => (
            <article className="history-item" key={item.id}>
              <div className="history-item__top">
                <strong>{item.overall_score}점</strong>
                <span>{new Date(item.created_at).toLocaleString("ko-KR")}</span>
              </div>
              <p>{item.input_text.slice(0, 100)}</p>
              <div className="history-item__bottom">
                <span>{item.formality_level}</span>
                <span>{item.tone_label}</span>
                <span>이슈 {item.issue_count}건</span>
              </div>
            </article>
          ))
        )}
      </div>
    </section>
  );
}