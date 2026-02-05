from sqlalchemy import create_engine
import pandas as pd
from backend.models import User
from flask import session
import time
import threading

df=pd.DataFrame()

# CONEXIÓN DB ==========
_engine = None
_engine_lock = threading.Lock()

def create_connection():
    """Crea o retorna una instancia singleton del engine de base de datos con reintentos."""
    global _engine
    
    with _engine_lock:
        if _engine is not None:
            try:
                # Verificar si la conexión sigue válida
                with _engine.connect() as conn:
                    pass
                return _engine
            except Exception:
                # Si falla, recrear el engine
                _engine = None
        
        # Intentar crear nueva conexión con reintentos
        max_retries = 3
        for attempt in range(max_retries):
            try:
                engine = create_engine(
                    'postgresql+psycopg2://app_user:sge02@10.0.29.117:5433/DW_ESTADISTICA',
                    pool_size=3,
                    max_overflow=2,
                    pool_pre_ping=True,
                    pool_recycle=1800,
                    pool_timeout=30,
                    echo_pool=False
                )
                # Verificar la conexión
                with engine.connect() as conn:
                    pass
                _engine = engine
                return _engine
            except Exception as e:
                print(f"Intento {attempt + 1}/{max_retries} - Failed to connect to database: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1 * (attempt + 1))  # Backoff exponencial
                else:
                    print("No se pudo establecer conexión después de todos los reintentos")
                    return None


def get_centro_asistencial():
    query="""
        SELECT cenasicod, cenasides 
        FROM dwsge.sgss_cmcas10
        WHERE estregcod ='1'
        ORDER BY id ASC 
    """
    
    engine = create_connection()
    if engine is None:
        print("Error: No se pudo obtener conexión a la base de datos")
        return pd.DataFrame(columns=['cenasicod', 'cenasides'])
    
    try:
        with engine.connect() as conn:
            df = pd.read_sql_query(query, conn)
        return df
    except Exception as e:
        print(f"Error ejecutando get_centro_asistencial: {e}")
        return pd.DataFrame(columns=['cenasicod', 'cenasides'])

def get_centro_asistencial_by_code_red(code_red):
    query = """
        SELECT 
            r.redasiscod,
            r.redasisdes,
            c.cenasicod,
            c.cenasides
        FROM dwsge.sgss_cmcas10 c
        LEFT JOIN dwsge.sgss_cmras10 r
            ON c.redasiscod = r.redasiscod
        WHERE c.redasiscod = %(code_red)s
        AND c.estregcod ='1'
    """
    
    engine = create_connection()
    if engine is None:
        print("Error: No se pudo obtener conexión a la base de datos")
        return pd.DataFrame(columns=['redasiscod', 'redasisdes', 'cenasicod', 'cenasides'])
    
    try:
        with engine.connect() as conn:
            df = pd.read_sql_query(query, conn, params={"code_red": str(code_red)})
        return df
    except Exception as e:
        print(f"Error ejecutando get_centro_asistencial_by_code_red: {e}")
        return pd.DataFrame(columns=['redasiscod', 'redasisdes', 'cenasicod', 'cenasides'])

def get_redes_asistenciales():
    query = """
        SELECT DISTINCT
            r.redasiscod,
            r.redasisdes
        FROM dwsge.sgss_cmcas10 c
        LEFT JOIN dwsge.sgss_cmras10 r
            ON c.redasiscod = r.redasiscod
        WHERE r.redasiscod IS NOT NULL
        AND c.estregcod ='1'
        ORDER BY r.redasisdes ASC
    """
    
    engine = create_connection()
    if engine is None:
        print("Error: No se pudo obtener conexión a la base de datos")
        return pd.DataFrame(columns=['redasiscod', 'redasisdes'])
    
    try:
        with engine.connect() as conn:
            df = pd.read_sql_query(query, conn)
        return df
    except Exception as e:
        print(f"Error ejecutando get_redes_asistenciales: {e}")
        return pd.DataFrame(columns=['redasiscod', 'redasisdes'])

def getNombreCentroAsistencial(request):
    codcas = request.form.get('codcas', '') or request.args.get('codcas', '')

    if not codcas:
        return ''

    try:
        df = get_centro_asistencial()
        if df.empty:
            return ''
        
        matches = df[df['cenasicod']==codcas]['cenasides'].values
        if len(matches) > 0:
            return matches[0]
        return ''
    except Exception as e:
        print(f"Error en getNombreCentroAsistencial: {e}")
        return ''


