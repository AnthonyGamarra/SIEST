export default function EmptyState({ message = 'Sin datos' }) {
  return (
    <div className="empty-state">
      <i className="bi bi-bar-chart" />
      <span>{message}</span>
    </div>
  );
}
