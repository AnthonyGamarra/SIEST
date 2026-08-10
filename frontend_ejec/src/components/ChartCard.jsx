export default function ChartCard({ title, subtitle, height = 340, flex = '1 1 380px', children }) {
  return (
    <div className="ejec-card chart-card" style={{ flex }}>
      <div className="chart-card-header">
        <div className="chart-card-title">{title}</div>
        {subtitle && <small className="chart-card-subtitle">{subtitle}</small>}
      </div>
      <div style={{ height }}>{children}</div>
    </div>
  );
}
