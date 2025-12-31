from sqlalchemy import create_engine
import pandas as pd

df=pd.DataFrame()

# CONEXIÓN DB ==========
def create_connection():
        try:
            engine = create_engine('postgresql+psycopg2://postgres:admin@10.0.29.117:5433/DW_ESTADISTICA')
            with engine.connect() as conn:
                pass
            return engine
        except Exception as e:
            print(f"Failed to connect to the database: {e}")
            return None


def get_centro_asistencial():

    query="""
        SELECT cenasicod, cenasidescor 
        FROM dwsge.sgss_cmcas10
        ORDER BY id ASC 
    """

    df=pd.read_sql_query(query, create_connection())
    return df
def getNombreCentroAsistencial(request):
    cod_cas = request.form.get('cod_cas', '')
    df = get_centro_asistencial()
    nombre_cas = df.loc[df['cenasicod'] == int(cod_cas), 'cenasidescor'].values
    if len(nombre_cas) > 0:
        return nombre_cas[0]
    else:
        return None