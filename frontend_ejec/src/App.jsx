import { useEffect, useState } from 'react';
import { getMeta, getHistoric, getComparativa, getFlujoArea, getDiagTreemap } from './api';
import { formatNumber } from './theme';
import KpiCard from './components/KpiCard';
import ChartCard from './components/ChartCard';
import AnioFilter from './components/AnioFilter';
import PacientesTotalesChart from './components/PacientesTotalesChart';
import EvolucionAnualChart from './components/EvolucionAnualChart';
import RankingRedChart from './components/RankingRedChart';
import ComorbilidadGrupoChart from './components/ComorbilidadGrupoChart';
import BurbujasChart from './components/BurbujasChart';
import TreemapChart from './components/TreemapChart';
import SankeyChart from './components/SankeyChart';

export default function App() {
  const [anios, setAnios] = useState([]);
  const [anioSel, setAnioSel] = useState(['TODOS']);
  const [historic, setHistoric] = useState(null);
  const [comparativa, setComparativa] = useState(null);
  const [flujo, setFlujo] = useState(null);
  const [treemap, setTreemap] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getMeta(), getHistoric()])
      .then(([meta, hist]) => {
        setAnios(meta.anios);
        setHistoric(hist);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (anioSel.length === 0) return;
    setComparativa(null);
    setFlujo(null);
    setTreemap(null);
    Promise.all([getComparativa(anioSel), getFlujoArea(anioSel), getDiagTreemap(anioSel)])
      .then(([comp, flujoData, treemapData]) => {
        setComparativa(comp);
        setFlujo(flujoData);
        setTreemap(treemapData.rows);
      })
      .catch((e) => setError(e.message));
  }, [anioSel]);

  if (loading) {
    return (
      <div className="ejec-root">
        <div className="loading-screen">Cargando modulo ejecutivo...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="ejec-root">
        <div className="alert-box">{error}</div>
      </div>
    );
  }

  const kpis = comparativa?.kpis;

  return (
    <div className="ejec-root">
      <header className="ejec-header">
        <div className="ejec-header-icon">
          <i className="bi bi-clipboard2-pulse" />
        </div>
        <div>
          <h2>Analitica por patologia de alto costo</h2>
          <p>Raras · Oncologico · Renal — version beta (React + Nivo)</p>
        </div>
      </header>

      <div className="ejec-card filter-card">
        <AnioFilter options={anios} value={anioSel} onChange={setAnioSel} />
      </div>

      <div className="kpi-row">
        {kpis ? (
          <>
            <KpiCard icon="bi-people-fill" title="Pacientes · Alto costo (Raras + Oncologico + Renal)" value={formatNumber(kpis.pacientes_alto_costo)} />
            <KpiCard icon="bi-clipboard2-pulse" title="Patologias activas" value={kpis.patologias_activas} color="#1BAF7A" />
            {kpis.top_red && (
              <KpiCard
                icon="bi-diagram-3"
                title="Mayor concentracion · Red"
                value={formatNumber(kpis.top_red.pacientes)}
                subtitle={`${kpis.top_red.patologia_label} en ${kpis.top_red.nombre}`}
                color="#EDA100"
              />
            )}
            {kpis.top_centro && (
              <KpiCard
                icon="bi-hospital"
                title="Mayor concentracion · Centro"
                value={formatNumber(kpis.top_centro.pacientes)}
                subtitle={`${kpis.top_centro.patologia_label} en ${kpis.top_centro.nombre}`}
                color="#EB6834"
              />
            )}
          </>
        ) : (
          <div className="kpi-skeleton">Calculando KPIs...</div>
        )}
      </div>

      <div className="chart-row">
        <ChartCard title="Pacientes por patologia de alto costo: Raras / Oncologico / Renal" subtitle="Total de pacientes por patologia (2019-2025)" height={340} flex="1 1 420px">
          <PacientesTotalesChart data={historic?.pacientes_totales} />
        </ChartCard>
        <ChartCard title="Evolucion anual · patologias de alto costo" subtitle="Pacientes por anio y patologia (2019-2025)" height={340} flex="2 1 560px">
          <EvolucionAnualChart data={historic?.evolucion_anual} />
        </ChartCard>
      </div>

      <ChartCard
        title="Ranking por red · patologias de alto costo"
        subtitle="Pacientes de Raras + Oncologico + Renal por red asistencial, distinguidos por patologia · top 15"
        height={Math.max(320, 34 * (comparativa?.ranking_red?.length || 10))}
        flex="1 1 100%"
      >
        <RankingRedChart data={comparativa?.ranking_red} />
      </ChartCard>

      <div className="chart-row">
        <ChartCard
          title="¿Que otras enfermedades tienen los pacientes de Oncologico? (alto costo)"
          subtitle="% de pacientes con Oncologico que en algun momento tambien tuvo cada diagnostico (2019-2025)."
          height={Math.max(320, 34 * (historic?.comorbilidad_oncologico?.length || 10))}
          flex="1 1 480px"
        >
          <ComorbilidadGrupoChart data={historic?.comorbilidad_oncologico} color="#0064AF" />
        </ChartCard>
        <ChartCard
          title="¿Que otras enfermedades tienen los pacientes de Renal? (alto costo)"
          subtitle="% de pacientes con Renal que en algun momento tambien tuvo cada diagnostico (2019-2025)."
          height={Math.max(320, 34 * (historic?.comorbilidad_renal?.length || 10))}
          flex="1 1 480px"
        >
          <ComorbilidadGrupoChart data={historic?.comorbilidad_renal} color="#1BAF7A" />
        </ChartCard>
      </div>

      <ChartCard
        title="Diagnosticos y servicios mas frecuentes por patologia de alto costo"
        subtitle="Top 10 diagnosticos (CIE-10) por patologia y, dentro de cada uno, sus servicios mas frecuentes · tamaño = pacientes · responde al filtro de Anio"
        height={480}
        flex="1 1 100%"
      >
        <TreemapChart rows={treemap} />
      </ChartCard>

      <ChartCard
        title="Todas las intersecciones entre comorbilidades"
        subtitle="Cada fila = una patologia; posicion, tamaño y color de cada burbuja = pacientes que comparte con la otra patologia · historico completo (diagonal excluida)"
        height={Math.max(420, 26 * (historic?.burbujas?.order?.length || 10))}
        flex="1 1 100%"
      >
        <BurbujasChart data={historic?.burbujas} />
      </ChartCard>

      <ChartCard
        title="Flujo de atencion: patologia de alto costo → area → servicio"
        subtitle="En que area y servicio se concentra la atencion de cada patologia de alto costo · responde al filtro de Anio. No representa el recorrido cronologico de un paciente."
        height={640}
        flex="1 1 100%"
      >
        <SankeyChart data={flujo} />
      </ChartCard>
    </div>
  );
}
