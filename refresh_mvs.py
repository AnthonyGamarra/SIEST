"""
Refresca las vistas materializadas del Modulo Ejecutivo de Patologias.
Corre como app_user (la app es OWNER de las MV, por eso puede refrescar sin
credenciales de administrador). Programar despues de cada carga/ETL de
dssge.mtd_lista_unica_pacientes (p.ej. tarea programada de Windows / pg_cron).

Uso:
    python refresh_mvs.py
"""
import os
import time
from dotenv import load_dotenv
load_dotenv()
import psycopg2

SCHEMA = "dssge"
# Orden: primero la base, luego los rollups que dependen de ella.
MVS = [
    "mv_ejec_base",
    "mv_ejec_pat_resumen",
    "mv_ejec_pat_detalle",
    "mv_ejec_pat_area",
    "mv_ejec_pat_servicio",
    "mv_ejec_pat_sexo_edad",
    "mv_ejec_pat_red",
    "mv_ejec_pat_centro",
    "mv_ejec_comorbilidad",
    "mv_ejec_pat_diag",
]


def main():
    uri = os.environ["DW_DATABASE_URI"].replace("postgresql+psycopg2://", "postgresql://")
    conn = psycopg2.connect(uri)
    conn.autocommit = True
    cur = conn.cursor()
    for mv in MVS:
        t = time.time()
        cur.execute(f"REFRESH MATERIALIZED VIEW {SCHEMA}.{mv}")
        print(f"  [{time.time()-t:6.1f}s] REFRESH {mv}")
    conn.close()
    print("Refresco completo.")


if __name__ == "__main__":
    main()
