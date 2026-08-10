import { ResponsiveBar } from '@nivo/bar';
import { colorForPatologia, formatNumber, FONT_FAMILY } from '../theme';
import EmptyState from './EmptyState';

// Capa custom: etiqueta de valor sobre cada barra (Nivo no trae "outside
// top" nativo para bar vertical).
function ValueLabels({ bars }) {
  return (
    <g>
      {bars.map((bar) => (
        <text
          key={bar.key}
          x={bar.x + bar.width / 2}
          y={bar.y - 8}
          textAnchor="middle"
          style={{ fontFamily: FONT_FAMILY, fontSize: 12, fontWeight: 700, fill: '#111827' }}
        >
          {formatNumber(bar.data.data.pacientes)}
        </text>
      ))}
    </g>
  );
}

export default function PacientesTotalesChart({ data }) {
  if (!data || data.length === 0) return <EmptyState />;

  return (
    <ResponsiveBar
      data={data}
      keys={['pacientes']}
      indexBy="label"
      margin={{ top: 30, right: 20, bottom: 40, left: 60 }}
      padding={0.4}
      colors={(bar) => colorForPatologia(bar.data.label)}
      enableLabel={false}
      enableGridY
      gridYValues={4}
      axisLeft={{ legend: 'Pacientes', legendPosition: 'middle', legendOffset: -50, format: formatNumber }}
      axisBottom={{ tickSize: 0, tickPadding: 8 }}
      theme={{
        fontFamily: FONT_FAMILY,
        axis: { ticks: { text: { fontSize: 12, fill: '#374151' } }, legend: { text: { fontSize: 12, fill: '#374151' } } },
        grid: { line: { stroke: '#F1F5F9' } },
      }}
      tooltip={({ data: d }) => (
        <div className="nivo-tooltip">
          <strong>{d.label}</strong>: {formatNumber(d.pacientes)} pacientes
        </div>
      )}
      layers={['grid', 'axes', 'bars', ValueLabels, 'markers', 'legends', 'annotations']}
      animate={false}
    />
  );
}
