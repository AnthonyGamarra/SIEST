import { ResponsiveSankey } from '@nivo/sankey';
import { colorForPatologia, formatNumber, FONT_FAMILY } from '../theme';
import EmptyState from './EmptyState';

const AREA_ORDER = ['CONSULTA EXTERNA', 'EMERGENCIA', 'HOSPITALIZACION', 'CENTRO QUIRURGICO'];

function titleCase(s) {
  return s.replace(/\w\S*/g, (t) => t[0].toUpperCase() + t.slice(1).toLowerCase());
}

function buildGraph({ pat_area, area_servicio }) {
  const nodesById = new Map();
  const links = [];

  const patLabels = Array.from(new Set(pat_area.map((r) => r.patologia_label)));
  for (const label of patLabels) {
    nodesById.set(`pat:${label}`, { id: `pat:${label}`, label, nodeColor: colorForPatologia(label) });
  }

  const areas = Array.from(new Set(pat_area.map((r) => r.area)));
  const orderedAreas = AREA_ORDER.filter((a) => areas.includes(a)).concat(areas.filter((a) => !AREA_ORDER.includes(a)));
  for (const area of orderedAreas) {
    nodesById.set(`area:${area}`, { id: `area:${area}`, label: titleCase(area), nodeColor: '#D1D5DB' });
  }

  for (const row of pat_area) {
    links.push({ source: `pat:${row.patologia_label}`, target: `area:${row.area}`, value: row.pacientes });
  }

  for (const row of area_servicio) {
    const servId = `serv:${row.area}::${row.servicio}`;
    if (!nodesById.has(servId)) {
      nodesById.set(servId, { id: servId, label: titleCase(row.servicio), nodeColor: '#E5E7EB' });
    }
    links.push({ source: `area:${row.area}`, target: servId, value: row.pacientes });
  }

  return { nodes: Array.from(nodesById.values()), links };
}

export default function SankeyChart({ data }) {
  if (!data || !data.pat_area || data.pat_area.length === 0) return <EmptyState />;
  const graph = buildGraph(data);

  return (
    <ResponsiveSankey
      data={graph}
      margin={{ top: 10, right: 160, bottom: 10, left: 120 }}
      align="justify"
      label="label"
      colors={(node) => node.nodeColor}
      nodeOpacity={1}
      nodeThickness={16}
      nodePaddingX={0}
      nodePaddingY={14}
      nodeBorderWidth={0}
      nodeBorderColor={{ from: 'color', modifiers: [['darker', 0.4]] }}
      linkOpacity={0.45}
      linkBlendMode="normal"
      linkContract={1}
      enableLinkGradient={false}
      labelPosition="outside"
      labelOrientation="horizontal"
      labelPadding={10}
      theme={{ fontFamily: FONT_FAMILY, labels: { text: { fontSize: 12, fill: '#374151' } } }}
      tooltip={({ link }) =>
        link ? (
          <div className="nivo-tooltip">
            {link.source.label} &rarr; {link.target.label}
            <br />
            {formatNumber(link.value)} pacientes
          </div>
        ) : null
      }
      animate={false}
    />
  );
}
