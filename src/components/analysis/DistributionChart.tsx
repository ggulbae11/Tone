import type { DistributionItem } from "../../types/analysis";

interface DistributionChartProps {
  items: DistributionItem[];
  title?: string;
}

export function DistributionChart({ items, title = "분포" }: DistributionChartProps) {
  const total = items.reduce((sum, item) => sum + item.count, 0) || 1;

  return (
    <section className="panel">
      <div className="panel__header">
        <h3>{title}</h3>
      </div>
      <div className="distribution-chart">
        {items.map((item) => {
          const width = `${(item.count / total) * 100}%`;
          return (
            <div className="distribution-chart__row" key={item.label}>
              <span>{item.label}</span>
              <div className="distribution-chart__track">
                <div className="distribution-chart__bar" style={{ width }} />
              </div>
              <strong>{item.count}</strong>
            </div>
          );
        })}
      </div>
    </section>
  );
}