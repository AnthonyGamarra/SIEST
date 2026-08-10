async function getJSON(path, params) {
  const url = new URL(path, window.location.origin);
  if (params) {
    for (const [key, values] of Object.entries(params)) {
      const list = Array.isArray(values) ? values : [values];
      for (const v of list) url.searchParams.append(key, v);
    }
  }
  const res = await fetch(url.pathname + url.search, { credentials: 'same-origin' });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error || `Error ${res.status}`);
  }
  return res.json();
}

export const getMeta = () => getJSON('/api/ejec/meta');
export const getHistoric = () => getJSON('/api/ejec/tab1/historic');
export const getComparativa = (anioList) => getJSON('/api/ejec/tab1/comparativa', { anio: anioList });
export const getFlujoArea = (anioList) => getJSON('/api/ejec/tab1/flujo-area', { anio: anioList });
export const getDiagTreemap = (anioList) => getJSON('/api/ejec/tab1/diag-treemap', { anio: anioList });
