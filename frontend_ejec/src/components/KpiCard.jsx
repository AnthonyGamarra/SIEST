import { tint } from '../theme';

export default function KpiCard({ icon, title, value, subtitle, color = '#0064AF' }) {
  return (
    <div className="ejec-card kpi-card" style={{ borderLeft: `3px solid ${color}` }}>
      <div className="kpi-icon" style={{ backgroundColor: tint(color) }}>
        <i className={`bi ${icon}`} style={{ color }} />
      </div>
      <div className="kpi-body">
        <div className="kpi-value">{value}</div>
        <small className="kpi-title">{title}</small>
        {subtitle && (
          <small className="kpi-subtitle" style={{ color }}>
            {subtitle}
          </small>
        )}
      </div>
    </div>
  );
}
