import { ResponsiveBar } from '@nivo/bar';
import { FONT_FAMILY } from '../theme';
import EmptyState from './EmptyState';

function ValueLabels({ bars }) {
  return (
    <g>
      {bars.map((bar) => (
        <text
          key={bar.key}
          x={bar.x + bar.width + 8}
          y={bar.y + bar.height / 2}
          dominantBaseline="middle"
          style={{ fontFamily: FONT_FAMILY, fontSize: 12, fontWeight: 700, fill: '#111827' }}
        >
          {`${bar.data.data.pacientes.toLocaleString('es-PE')} (${bar.data.data.pct.toFixed(1)}%)`}
        </text>
      ))}
    </g>
  );
}

export default function ComorbilidadGrupoChart({ data, color }) {
  if (!data || data.length === 0) return <EmptyState />;
  const sorted = [...data].sort((a, b) => a.pct - b.pct);
  const maxPct = Math.max(...sorted.map((d) => d.pct), 10);

  return (
    <ResponsiveBar
      data={sorted}
      keys={['pct']}
      indexBy="label"
      layout="horizontal"
      margin={{ top: 10, right: 130, bottom: 40, left: 190 }}
      padding={0.35}
      colors={color}
      valueScale={{ type: 'linear', min: 0, max: maxPct * 1.3 }}
      enableLabel={false}
      axisBottom={{ legend: '% de pacientes', legendPosition: 'middle', legendOffset: 32, format: (v) => `${v}%` }}
      axisLeft={{ tickSize: 0, tickPadding: 10 }}
      theme={{
        fontFamily: FONT_FAMILY,
        axis: { ticks: { text: { fontSize: 12, fill: '#374151' } }, legend: { text: { fontSize: 12, fill: '#374151' } } },
        grid: { line: { stroke: '#F1F5F9' } },
      }}
      tooltip={({ data: d }) => (
        <div className="nivo-tooltip">
          <strong>{d.label}</strong>
          <br />
          {d.pct.toFixed(1)}% ({d.pacientes.toLocaleString('es-PE')} pacientes)
        </div>
      )}
      layers={['grid', 'axes', 'bars', ValueLabels, 'markers', 'legends', 'annotations']}
      animate={false}
    />
  );
}
