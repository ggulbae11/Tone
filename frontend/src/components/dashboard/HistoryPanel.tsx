import type { HistoryItem } from "../../types/analysis";

interface HistoryPanelProps {
  items: HistoryItem[];
  onClear?: () => void;
  onSelect?: (item: HistoryItem) => void;
}

export function HistoryPanel({ items, onClear, onSelect }: HistoryPanelProps) {
  return (
    <section className="panel">
      <div className="panel__header">
        <h3>최근 분석 이력</h3>
        {onClear && items.length > 0 ? (
          <button type="button" className="clear-button" onClick={onClear}>
            기록 삭제
          </button>
        ) : null}
      </div>
      <div className="history-list">
        {items.length === 0 ? (
          <p className="empty-state">아직 저장된 분석 이력이 없습니다.</p>
        ) : (
          items.map((item) => (
            <button
              key={item.id}
              type="button"
              className="history-item history-item--clickable"
              onClick={() => onSelect?.(item)}
            >
              <div className="history-item__top">
                <strong>{item.overall_score}점</strong>
                <span>{new Date(item.created_at).toLocaleString("ko-KR")}</span>
              </div>
              <p>{item.input_text.slice(0, 80)}</p>
              <div className="history-item__bottom">
                <span>{item.formality_level}</span>
                <span>불일치 {item.issue_count}건</span>
              </div>
            </button>
          ))
        )}
      </div>
    </section>
  );
}
