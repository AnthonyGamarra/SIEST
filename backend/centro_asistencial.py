from sqlalchemy import create_engine
import pandas as pd
from backend.models import User
from flask import session

df=pd.DataFrame()

# CONEXIÓN DB ==========
def create_connection():
        try:
            engine = create_engine('postgresql+psycopg2://postgres:4dm1n@10.0.29.117:5433/DW_ESTADISTICA')
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
        WHERE estregcod= '1'
        ORDER BY id ASC 
    """

    df=pd.read_sql_query(query, create_connection())
    return df
def get_centro_asistencial_by_code_red(code_red):
    query = """
        SELECT 
            r.redasiscod,
            r.redasisdes,
            c.cenasicod,
            c.cenasidescor
        FROM dwsge.sgss_cmcas10 c
        LEFT JOIN dwsge.sgss_cmras10 r
            ON c.redasiscod = r.redasiscod
        WHERE c.redasiscod = %(code_red)s
        AND c.estregcod= '1'
    """
    df=pd.read_sql_query(query,create_connection(),params={"code_red": str(code_red)})
    return df

def getNombreCentroAsistencial(request):
    codcas = request.form.get('codcas', '') or request.args.get('codcas', '')

    if not codcas:
        return ''

    df=get_centro_asistencial()
    
    name_centro=df[df['cenasicod']==codcas]['cenasidescor'].values[0]

    return name_centro


