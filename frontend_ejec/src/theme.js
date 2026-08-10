// Misma paleta categorica validada (CVD-safe) que dashboard_ejec.py — orden
// fijo, no reordenar ni ciclar.
export const PALETTE = ['#2A78D6', '#008300', '#E87BA4', '#EDA100', '#1BAF7A', '#EB6834', '#4A3AA7', '#E34948'];

export const BRAND = '#0064AF';
export const MUTED = '#6B7280';
export const BORDER = '#E5E7EB';

export const PATOLOGIA_COLORS = {
  Oncologico: BRAND,
  Renal: PALETTE[4],
  Raras: PALETTE[3],
};

export const FONT_FAMILY = "Inter, 'Segoe UI', Calibri, sans-serif";

export function colorForPatologia(label) {
  return PATOLOGIA_COLORS[label] || BRAND;
}

function hexToRgb(hex) {
  const h = hex.replace('#', '');
  return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
}

export function tint(hex, alpha = 0.14) {
  const [r, g, b] = hexToRgb(hex);
  return `rgba(${r},${g},${b},${alpha})`;
}

export function soften(hex, alpha = 0.45) {
  return tint(hex, alpha);
}

// Interpola linealmente entre dos colores en RGB (suficiente para una escala
// secuencial de 2 puntos, igual que el colorscale de la version Plotly).
export function sequentialScale(t, from = '#CDE2FB', to = '#104281') {
  const [r1, g1, b1] = hexToRgb(from);
  const [r2, g2, b2] = hexToRgb(to);
  const r = Math.round(r1 + (r2 - r1) * t);
  const g = Math.round(g1 + (g2 - g1) * t);
  const b = Math.round(b1 + (b2 - b1) * t);
  return `rgb(${r},${g},${b})`;
}

export function formatNumber(n) {
  if (n === null || n === undefined || Number.isNaN(n)) return '0';
  return Math.round(n).toLocaleString('es-PE');
}
