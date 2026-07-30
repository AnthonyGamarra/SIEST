"""
Crea unicamente las vistas materializadas nuevas de EXTRA_ROLLUPS (definidas
en build_mvs.py), sin tocar ni reconstruir ninguna de las 9 vistas existentes
del Modulo Ejecutivo de Patologias. Son vistas independientes: solo leen de
dssge.mv_ejec_base (ya poblada) y ninguna otra vista depende de ellas.

Uso (PowerShell):
    $env:DW_ADMIN_URI="postgresql://postgres:PASSWORD@10.0.29.117:5433/DW_ESTADISTICA"
    python build_mvs_extra.py
"""
import time
import psycopg2

from build_mvs import ADMIN_URI, APP_ROLE, SCHEMA, ROLLUPS, EXTRA_ROLLUPS, run


def main():
    conn = psycopg2.connect(ADMIN_URI)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("SELECT current_user")
    print("Conectado como:", cur.fetchone()[0])

    print(f"\n1) Creando {len(EXTRA_ROLLUPS)} vistas nuevas (sin tocar las existentes)...")
    for mv in EXTRA_ROLLUPS:
        cur.execute(f"DROP MATERIALIZED VIEW IF EXISTS {SCHEMA}.{mv} CASCADE")
        run(cur, mv, ROLLUPS[mv])

    print(f"2) Transfiriendo OWNER a {APP_ROLE}...")
    for mv in EXTRA_ROLLUPS:
        cur.execute(f"ALTER MATERIALIZED VIEW {SCHEMA}.{mv} OWNER TO {APP_ROLE}")

    print("\n3) Conteos:")
    for mv in EXTRA_ROLLUPS:
        cur.execute(f"SELECT COUNT(*) FROM {SCHEMA}.{mv}")
        print(f"  {mv:26s} {cur.fetchone()[0]:>12,} filas")

    conn.close()
    print("\nListo. Vistas nuevas creadas, el resto del modulo no se toco.")


if __name__ == "__main__":
    main()
