import { ResponsiveBar } from '@nivo/bar';
import { colorForPatologia, formatNumber, FONT_FAMILY } from '../theme';
import EmptyState from './EmptyState';

const PATOLOGIAS = ['Oncologico', 'Renal', 'Raras'];

export default function RankingRedChart({ data }) {
  if (!data || data.length === 0) return <EmptyState />;
  const keys = PATOLOGIAS.filter((k) => data.some((row) => row[k] !== undefined));

  return (
    <ResponsiveBar
      data={data}
      keys={keys}
      indexBy="redasisdes"
      layout="horizontal"
      groupMode="stacked"
      margin={{ top: 10, right: 30, bottom: 40, left: 220 }}
      padding={0.3}
      colors={(bar) => colorForPatologia(bar.id)}
      valueFormat={formatNumber}
      enableLabel
      labelTextColor="white"
      label={(d) => formatNumber(d.value)}
      axisBottom={{ legend: 'Pacientes', legendPosition: 'middle', legendOffset: 32, format: formatNumber }}
      axisLeft={{ tickSize: 0, tickPadding: 10 }}
      theme={{
        fontFamily: FONT_FAMILY,
        axis: { ticks: { text: { fontSize: 12, fill: '#374151' } }, legend: { text: { fontSize: 12, fill: '#374151' } } },
        grid: { line: { stroke: '#F1F5F9' } },
        labels: { text: { fontSize: 12, fontWeight: 700 } },
      }}
      legends={[
        {
          dataFrom: 'keys',
          anchor: 'top',
          direction: 'row',
          translateY: -10,
          itemWidth: 100,
          itemHeight: 20,
          symbolShape: 'circle',
        },
      ]}
      tooltip={({ id, value, indexValue }) => (
        <div className="nivo-tooltip">
          <strong>{indexValue}</strong>
          <br />
          {id}: {formatNumber(value)} pacientes
        </div>
      )}
      animate={false}
    />
  );
}
