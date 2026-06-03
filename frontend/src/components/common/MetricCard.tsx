interface MetricCardProps {
  title: string;
  value: string;
  subtitle: string;
  accent?: "red" | "orange" | "blue" | "green";
}

export function MetricCard({ title, value, subtitle, accent = "blue" }: MetricCardProps) {
  return (
    <article className={`metric-card metric-card--${accent}`}>
      <p className="metric-card__title">{title}</p>
      <strong className="metric-card__value">{value}</strong>
      <p className="metric-card__subtitle">{subtitle}</p>
    </article>
  );
}
