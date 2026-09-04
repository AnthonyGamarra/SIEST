"""
Refresca las vistas materializadas del Reporteador self-service (anio en
curso, 2026). Corre como app_user (la app es OWNER de las MV, por eso puede
refrescar sin credenciales de administrador). Programar despues de cada
carga/ETL de dwsge.dwe_consulta_externa_homologacion (particion 2026).

Uso:
    python refresh_mvs_diag.py
"""
import os
import time
from dotenv import load_dotenv
load_dotenv()
import psycopg2

# Lista hardcodeada (no se importa de build_mvs_diag.py a proposito: ese
# script exige DW_ADMIN_URI al importarse, y este refresh corre como
# app_user sin esa credencial). Si se agrega/renombra un rollup en
# build_mvs_diag.py, actualizar tambien esta lista.
ANIO_ACTUAL = "2026"
ALL_MVS = [
    f"mv_diag_{ANIO_ACTUAL}_base",
    f"mv_diag_{ANIO_ACTUAL}_servicio",
    f"mv_diag_{ANIO_ACTUAL}_red",
    f"mv_diag_{ANIO_ACTUAL}_centro",
    f"mv_diag_{ANIO_ACTUAL}_actividad",
    f"mv_diag_{ANIO_ACTUAL}_subactividad",
    f"mv_diag_{ANIO_ACTUAL}_variable",
    f"mv_diag_{ANIO_ACTUAL}_capitulo",
    f"mv_diag_{ANIO_ACTUAL}_sexo",
    f"mv_diag_{ANIO_ACTUAL}_edad",
    f"mv_diag_{ANIO_ACTUAL}_servicio_sexo",
    f"mv_diag_{ANIO_ACTUAL}_capitulo_edad",
    f"mv_diag_{ANIO_ACTUAL}_red_servicio",
]


def main():
    uri = os.environ["DW_DATABASE_URI"].replace("postgresql+psycopg2://", "postgresql://")
    conn = psycopg2.connect(uri)
    conn.autocommit = True
    cur = conn.cursor()
    for mv in ALL_MVS:
        t = time.time()
        cur.execute(f"REFRESH MATERIALIZED VIEW dssge.{mv}")
        print(f"  [{time.time()-t:6.1f}s] REFRESH {mv}")
    conn.close()
    print("Refresco completo.")


if __name__ == "__main__":
    main()
