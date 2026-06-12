import type { HistoryItem } from "../../types/analysis";

interface HistoryPanelProps {
  items: HistoryItem[];
  onSelect: (item: HistoryItem) => void;
}

export function HistoryPanel({ items, onSelect, onScroll }: HistoryPanelProps & { onScroll?: (e: React.UIEvent<HTMLDivElement>) => void }) {
  return (
    <section className="panel">
      <div className="panel__header">
        <h3>최근 분석 이력</h3>
      </div>
      <div className="history-list" >
        {items.length === 0 ? (
          <p className="empty-state">아직 저장된 분석 이력이 없습니다.</p>
        ) : (
          items.map((item) => (
            <article className="history-item" key={item.id} onClick={() => { console.log("clicked:", item); onSelect(item); }} style={{ cursor: "pointer" }} >
              <div className="history-item__top">
                <strong>{Math.round(item.overall_score)}점</strong>
                <span>{new Date(item.created_at).toLocaleString("ko-KR", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", })}</span>
              </div>
              <p className="history-preview">{item.input_text}</p>
              <div className="history-item__bottom">
                <span className="history-badge history-badge--primary">{item.formality_level}</span>
                <span className="history-badge history-badge--warning">이슈 {item.issue_count}건</span>
              </div>
            </article>
          ))
        )}
      </div>
    </section>
  );
}