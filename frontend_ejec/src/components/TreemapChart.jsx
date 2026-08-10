import { ResponsiveTreeMap } from '@nivo/treemap';
import { colorForPatologia, formatNumber, FONT_FAMILY } from '../theme';
import EmptyState from './EmptyState';

function buildHierarchy(rows) {
  const root = { name: 'root', children: [] };
  const patMap = new Map();
  for (const row of rows) {
    if (!patMap.has(row.patologia_label)) {
      const patNode = { name: row.patologia_label, children: [] };
      patMap.set(row.patologia_label, patNode);
      root.children.push(patNode);
    }
    const patNode = patMap.get(row.patologia_label);
    let diagNode = patNode.children.find((c) => c.name === row.diagnostico);
    if (!diagNode) {
      diagNode = { name: row.diagnostico, children: [] };
      patNode.children.push(diagNode);
    }
    diagNode.children.push({ name: row.servicio, value: row.pacientes });
  }
  return root;
}

export default function TreemapChart({ rows }) {
  if (!rows || rows.length === 0) return <EmptyState />;
  const data = buildHierarchy(rows);

  return (
    <ResponsiveTreeMap
      data={data}
      identity="name"
      value="value"
      valueFormat={formatNumber}
      leavesOnly={false}
      innerPadding={2}
      outerPadding={2}
      margin={{ top: 40, right: 10, bottom: 10, left: 10 }}
      label={(node) => `${node.id}`}
      labelSkipSize={28}
      enableParentLabel
      parentLabelPosition="top"
      parentLabelSize={28}
      borderWidth={1}
      borderColor="white"
      colors={(node) => colorForPatologia(node.pathComponents[1] || node.pathComponents[0])}
      nodeOpacity={1}
      theme={{ fontFamily: FONT_FAMILY, labels: { text: { fontSize: 12 } } }}
      tooltip={({ node }) => (
        <div className="nivo-tooltip">
          <strong>{node.pathComponents.slice(1).join(' · ')}</strong>
          <br />
          {formatNumber(node.value)} pacientes
        </div>
      )}
      animate={false}
    />
  );
}
