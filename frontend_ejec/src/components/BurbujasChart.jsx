import { sequentialScale, formatNumber } from '../theme';
import EmptyState from './EmptyState';

const SIZE_MIN = 10;
const SIZE_MAX = 42;
const COLOR_FROM = '#CDE2FB';
const COLOR_TO = '#104281';
const ROW_HEIGHT = 26;
const TICKS = [0, 0.25, 0.5, 0.75, 1];

// @nivo/scatterplot solo permite color por serie (no por punto), asi que
// para esta nube de burbujas (color+tamaño continuos por punto, un solo eje
// categorico) se arma a mano con divs posicionados en % — mas simple y
// robusto que forzar la API de Nivo para este caso.
export default function BurbujasChart({ data }) {
  if (!data || !data.puntos || data.puntos.length === 0) return <EmptyState />;
  const { order, puntos } = data;
  const maxPacientes = Math.max(...puntos.map((p) => p.pacientes));

  const rows = order.map((label) => ({
    label,
    points: puntos.filter((p) => p.patologia_a_label === label),
  }));

  const sizeFor = (pacientes) => SIZE_MIN + (SIZE_MAX - SIZE_MIN) * Math.sqrt(pacientes / maxPacientes);
  const colorFor = (pacientes) => sequentialScale(Math.sqrt(pacientes / maxPacientes), COLOR_FROM, COLOR_TO);

  return (
    <div className="bubbles-chart">
      <div className="color-scale-legend">
        <span>Pacientes en comun</span>
        <div className="color-scale-bar" style={{ background: `linear-gradient(to right, ${COLOR_FROM}, ${COLOR_TO})` }} />
        <span>{formatNumber(maxPacientes)}</span>
      </div>
      <div className="bubbles-rows">
        {rows.map((row) => (
          <div className="bubble-row" key={row.label} style={{ height: ROW_HEIGHT }}>
            <div className="bubble-row-label" title={row.label}>
              {row.label}
            </div>
            <div className="bubble-row-track">
              {row.points.map((p) => {
                const size = sizeFor(p.pacientes);
                return (
                  <div
                    key={p.patologia_b_label}
                    className="bubble"
                    style={{
                      left: `${(p.pacientes / maxPacientes) * 100}%`,
                      width: size,
                      height: size,
                      backgroundColor: colorFor(p.pacientes),
                    }}
                  >
                    <div className="bubble-tooltip">
                      <strong>
                        {row.label} &cap; {p.patologia_b_label}
                      </strong>
                      <br />
                      {formatNumber(p.pacientes)} pacientes
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
      <div className="bubbles-axis">
        <div className="bubble-row-label" />
        <div className="bubble-row-track">
          {TICKS.map((t) => (
            <span key={t} className="bubbles-axis-tick" style={{ left: `${t * 100}%` }}>
              {formatNumber(maxPacientes * t)}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
