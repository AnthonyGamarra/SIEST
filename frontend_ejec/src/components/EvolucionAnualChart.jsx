import { ResponsiveLine } from '@nivo/line';
import { colorForPatologia, formatNumber, FONT_FAMILY } from '../theme';
import EmptyState from './EmptyState';

function toSeries(rows) {
  const byLabel = new Map();
  for (const row of rows) {
    if (!byLabel.has(row.label)) byLabel.set(row.label, []);
    byLabel.get(row.label).push({ x: row.anio, y: row.pacientes });
  }
  return Array.from(byLabel.entries()).map(([label, data]) => ({ id: label, data }));
}

export default function EvolucionAnualChart({ data }) {
  if (!data || data.length === 0) return <EmptyState />;
  const series = toSeries(data);

  return (
    <ResponsiveLine
      data={series}
      margin={{ top: 40, right: 30, bottom: 50, left: 60 }}
      xScale={{ type: 'point' }}
      yScale={{ type: 'linear', min: 0, max: 'auto', stacked: false }}
      colors={(s) => colorForPatologia(s.id)}
      lineWidth={3}
      pointSize={8}
      pointBorderWidth={2}
      pointBorderColor="white"
      enablePointLabel
      pointLabel={(d) => formatNumber(d.y)}
      pointLabelYOffset={-14}
      enableGridX={false}
      gridYValues={4}
      axisLeft={{ legend: 'Pacientes', legendPosition: 'middle', legendOffset: -50, format: formatNumber }}
      axisBottom={{ tickSize: 0, tickPadding: 8 }}
      useMesh
      theme={{
        fontFamily: FONT_FAMILY,
        axis: { ticks: { text: { fontSize: 12, fill: '#374151' } }, legend: { text: { fontSize: 12, fill: '#374151' } } },
        grid: { line: { stroke: '#F1F5F9' } },
      }}
      legends={[
        {
          anchor: 'top',
          direction: 'row',
          translateY: -30,
          itemWidth: 110,
          itemHeight: 20,
          symbolShape: 'circle',
        },
      ]}
      animate={false}
    />
  );
}
