from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / ".env"
load_dotenv(dotenv_path=ENV_PATH)

from backend.sqlserver_connection import get_sqlserver_connection


TABLE_NAME = "dbo.DATA_ESTABLECIMIENTO_ESSALUD_FINAL_V2"
AUDIT_TABLE = "dbo.AUD_ESTABLECIMIENTO"


EDITABLE_FIELDS = {
    "COD_EESS",
    "COD_SES",
    "NOMBRE_ESTABLECIMIENTO",
    "RED_ASISTENCIAL",
    "RED_ABREVIADA",
    "TIPO_ESSALUD",
    "NIVEL_ESSALUD",
    "TIPO_CENTRO",
    "DESCRIPCION_TIPO",
    "ESTADO_ESSALUD",
    "ACTIVO_ESSALUD",
    "DEPARTAMENTO",
    "PROVINCIA",
    "DISTRITO",
    "UBIGEO",
    "DIRECCION",
    "CATEGORIA",
    "TIPO_DOC_CATEGORIZACION",
    "NRO_DOC_CATEGORIZACION",
    "RESOLUCION_CATEGORIZACION_GCPS",
    "INICIO_ACTIVIDAD",
    "ESTADO_RENIPRESS",
    "LATITUD",
    "LONGITUD",
    "CAMAS",
    "NUMERO_RESOLUCION_ESSALUD",
    "LINK_RESOLUCION",
    "FUENTE_RENIPRESS",
    "OBSERVACION",
    "OBSERVACION_CONSOLIDACION",
    "CONDICION_CENTRO",
    "ES_OFICIAL",
    "ENTIDAD_VALIDADORA",
}


def _rows_to_dicts(cursor, rows):
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in rows]


def _row_to_dict(cursor, row):
    if not row:
        return None
    columns = [col[0] for col in cursor.description]
    return dict(zip(columns, row))


def _audit_text(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, Decimal):
        return format(value, "f")
    return str(value)


def obtener_resumen_ejecutivo():
    sql = f"""
    SELECT
        COUNT(*) AS TOTAL_VERSIONES,

        SUM(
            CASE
                WHEN ES_VERSION_ACTUAL = 1
                THEN 1 ELSE 0
            END
        ) AS TOTAL_MAESTRO_ACTUAL,

        SUM(
            CASE
                WHEN ES_VERSION_ACTUAL = 1
                 AND ES_OFICIAL = 1
                THEN 1 ELSE 0
            END
        ) AS TOTAL_OFICIALES,

        SUM(
            CASE
                WHEN ES_VERSION_ACTUAL = 1
                 AND ES_OFICIAL = 1
                 AND CONDICION_CENTRO = 'PROPIO'
                THEN 1 ELSE 0
            END
        ) AS TOTAL_PROPIOS,

        SUM(
            CASE
                WHEN ES_VERSION_ACTUAL = 1
                 AND ES_OFICIAL = 1
                 AND CONDICION_CENTRO = 'EXTRA'
                THEN 1 ELSE 0
            END
        ) AS TOTAL_EXTRAS,

        SUM(
            CASE
                WHEN ES_VERSION_ACTUAL = 1
                 AND ES_OFICIAL = 0
                THEN 1 ELSE 0
            END
        ) AS TOTAL_FUERA_OFICIAL,

        SUM(
            CASE
                WHEN ES_VERSION_ACTUAL = 0
                THEN 1 ELSE 0
            END
        ) AS TOTAL_VERSIONES_HISTORICAS,

        SUM(
            CASE
                WHEN ES_VERSION_ACTUAL = 1
                 AND ES_OFICIAL = 1
                 AND ACTIVO_ESSALUD = 1
                THEN 1 ELSE 0
            END
        ) AS TOTAL_OPERATIVOS

    FROM {TABLE_NAME}
    """

    conn = None
    try:
        conn = get_sqlserver_connection()
        cursor = conn.cursor()
        cursor.execute(sql)
        return _row_to_dict(cursor, cursor.fetchone()) or {}
    finally:
        if conn is not None:
            conn.close()


def obtener_distribucion(campo, top=20):
    allowed = {
        "RED_ASISTENCIAL",
        "NIVEL_ESSALUD",
        "CATEGORIA",
        "DEPARTAMENTO",
        "CONDICION_CENTRO",
        "ENTIDAD_VALIDADORA",
    }

    if campo not in allowed:
        raise ValueError(f"Campo de distribución no permitido: {campo}")

    top = max(1, min(int(top), 100))

    sql = f"""
    SELECT TOP {top}
        ISNULL(NULLIF(LTRIM(RTRIM([{campo}])), ''), 'SIN INFORMACIÓN') AS CATEGORIA,
        COUNT(*) AS CANTIDAD
    FROM {TABLE_NAME}
    WHERE ES_VERSION_ACTUAL = 1
      AND ES_OFICIAL = 1
    GROUP BY
        ISNULL(NULLIF(LTRIM(RTRIM([{campo}])), ''), 'SIN INFORMACIÓN')
    ORDER BY COUNT(*) DESC, CATEGORIA
    """

    conn = None
    try:
        conn = get_sqlserver_connection()
        cursor = conn.cursor()
        cursor.execute(sql)
        return _rows_to_dicts(cursor, cursor.fetchall())
    finally:
        if conn is not None:
            conn.close()


def obtener_calidad_maestro():
    sql = f"""
    SELECT
        COUNT(*) AS TOTAL,

        SUM(CASE WHEN NULLIF(LTRIM(RTRIM(RENIPRESS)), '') IS NOT NULL
                 THEN 1 ELSE 0 END) AS CON_RENIPRESS,

        SUM(CASE WHEN NULLIF(LTRIM(RTRIM(UBIGEO)), '') IS NOT NULL
                 THEN 1 ELSE 0 END) AS CON_UBIGEO,

        SUM(CASE WHEN LATITUD IS NOT NULL AND LONGITUD IS NOT NULL
                 THEN 1 ELSE 0 END) AS CON_COORDENADAS,

        SUM(CASE WHEN NULLIF(LTRIM(RTRIM(CATEGORIA)), '') IS NOT NULL
                 THEN 1 ELSE 0 END) AS CON_CATEGORIA,

        SUM(CASE WHEN
                    NULLIF(LTRIM(RTRIM(RESOLUCION_CATEGORIZACION_GCPS)), '') IS NOT NULL
                 OR NULLIF(LTRIM(RTRIM(NUMERO_RESOLUCION_ESSALUD)), '') IS NOT NULL
                 THEN 1 ELSE 0 END) AS CON_RESOLUCION,

        SUM(CASE WHEN NULLIF(LTRIM(RTRIM(DIRECCION)), '') IS NOT NULL
                 THEN 1 ELSE 0 END) AS CON_DIRECCION,

        SUM(CASE WHEN NULLIF(LTRIM(RTRIM(RED_ASISTENCIAL)), '') IS NOT NULL
                 THEN 1 ELSE 0 END) AS CON_RED,

        SUM(CASE WHEN NULLIF(LTRIM(RTRIM(NIVEL_ESSALUD)), '') IS NOT NULL
                 THEN 1 ELSE 0 END) AS CON_NIVEL

    FROM {TABLE_NAME}
    WHERE ES_VERSION_ACTUAL = 1
      AND ES_OFICIAL = 1
    """

    conn = None
    try:
        conn = get_sqlserver_connection()
        cursor = conn.cursor()
        cursor.execute(sql)
        return _row_to_dict(cursor, cursor.fetchone()) or {}
    finally:
        if conn is not None:
            conn.close()


def buscar_establecimientos(
    texto=None,
    condicion_centro=None,
    vigencia="ACTIVO",
    limite=1000,
):
    """
    ACTIVO:
        solo centros oficiales y versión actual.

    HISTORICO:
        todo el maestro: oficiales, fuera del maestro oficial y versiones
        históricas generadas por cambios de RENIPRESS.
    """
    limite = max(1, min(int(limite), 5000))

    where = []
    params = []

    vigencia = str(vigencia or "ACTIVO").strip().upper()

    if vigencia == "ACTIVO":
        where.extend([
            "ES_VERSION_ACTUAL = 1",
            "ES_OFICIAL = 1",
        ])
    elif vigencia == "HISTORICO":
        pass
    else:
        raise ValueError("vigencia debe ser ACTIVO o HISTORICO.")

    texto = (texto or "").strip().upper()

    if texto:
        parametro = f"%{texto}%"
        where.append(
            """
            (
                   UPPER(ISNULL(COD_EESS, '')) LIKE ?
                OR UPPER(ISNULL(COD_SES, '')) LIKE ?
                OR UPPER(ISNULL(RENIPRESS, '')) LIKE ?
                OR UPPER(ISNULL(NOMBRE_ESTABLECIMIENTO, '')) LIKE ?
                OR UPPER(ISNULL(RED_ASISTENCIAL, '')) LIKE ?
            )
            """
        )
        params.extend([parametro] * 5)

    if condicion_centro:
        where.append("CONDICION_CENTRO = ?")
        params.append(str(condicion_centro).strip().upper())

    where_sql = " AND ".join(where) if where else "1 = 1"

    sql = f"""
    SELECT TOP {limite}
        ID_REGISTRO,
        ID_ESTABLECIMIENTO,
        COD_EESS,
        COD_SES,
        RENIPRESS,
        NOMBRE_ESTABLECIMIENTO,
        RED_ASISTENCIAL,
        NIVEL_ESSALUD,
        TIPO_CENTRO,
        CATEGORIA,
        ACTIVO_ESSALUD,
        ES_OFICIAL,
        ENTIDAD_VALIDADORA,
        CONDICION_CENTRO,
        ES_VERSION_ACTUAL,
        FECHA_CAMBIO_RENIPRES
    FROM {TABLE_NAME}
    WHERE {where_sql}
    ORDER BY
        ES_VERSION_ACTUAL DESC,
        ES_OFICIAL DESC,
        CASE WHEN CONDICION_CENTRO = 'PROPIO' THEN 0 ELSE 1 END,
        NOMBRE_ESTABLECIMIENTO,
        ID_REGISTRO DESC
    """

    conn = None
    try:
        conn = get_sqlserver_connection()
        cursor = conn.cursor()
        cursor.execute(sql, *params)
        return _rows_to_dicts(cursor, cursor.fetchall())
    finally:
        if conn is not None:
            conn.close()


def obtener_establecimiento_por_id(id_registro):
    sql = f"""
    SELECT
        ID_REGISTRO,
        ID_ESTABLECIMIENTO,
        COD_EESS,
        COD_SES,
        RENIPRESS,
        COD_RENIPRES_ANTERIOR,
        ID_REGISTRO_ANTERIOR,
        ES_VERSION_ACTUAL,
        FECHA_CAMBIO_RENIPRES,
        NOMBRE_ESTABLECIMIENTO,
        RED_ASISTENCIAL,
        RED_ABREVIADA,
        TIPO_ESSALUD,
        NIVEL_ESSALUD,
        TIPO_CENTRO,
        DESCRIPCION_TIPO,
        ESTADO_ESSALUD,
        ACTIVO_ESSALUD,
        DEPARTAMENTO,
        PROVINCIA,
        DISTRITO,
        UBIGEO,
        DIRECCION,
        CATEGORIA,
        TIPO_DOC_CATEGORIZACION,
        NRO_DOC_CATEGORIZACION,
        RESOLUCION_CATEGORIZACION_GCPS,
        INICIO_ACTIVIDAD,
        ESTADO_RENIPRESS,
        LATITUD,
        LONGITUD,
        CAMAS,
        NUMERO_RESOLUCION_ESSALUD,
        LINK_RESOLUCION,
        FUENTE_RENIPRESS,
        APROBADO_GCPS,
        CLASIFICACION_CONCILIACION,
        OBSERVACION,
        OBSERVACION_CONSOLIDACION,
        CONDICION_CENTRO,
        ES_OFICIAL,
        ENTIDAD_VALIDADORA
    FROM {TABLE_NAME}
    WHERE ID_REGISTRO = ?
    """

    conn = None
    try:
        conn = get_sqlserver_connection()
        cursor = conn.cursor()
        cursor.execute(sql, int(id_registro))
        return _row_to_dict(cursor, cursor.fetchone())
    finally:
        if conn is not None:
            conn.close()


def obtener_historial_establecimiento(id_establecimiento):
    sql = f"""
    SELECT
        ID_REGISTRO,
        ID_ESTABLECIMIENTO,
        RENIPRESS,
        COD_RENIPRES_ANTERIOR,
        ID_REGISTRO_ANTERIOR,
        ES_VERSION_ACTUAL,
        FECHA_CAMBIO_RENIPRES,
        NOMBRE_ESTABLECIMIENTO,
        ACTIVO_ESSALUD,
        ES_OFICIAL,
        ENTIDAD_VALIDADORA,
        ESTADO_RENIPRESS
    FROM {TABLE_NAME}
    WHERE ID_ESTABLECIMIENTO = ?
    ORDER BY ID_REGISTRO DESC
    """

    conn = None
    try:
        conn = get_sqlserver_connection()
        cursor = conn.cursor()
        cursor.execute(sql, int(id_establecimiento))
        return _rows_to_dicts(cursor, cursor.fetchall())
    finally:
        if conn is not None:
            conn.close()


def obtener_auditoria_establecimiento(id_establecimiento):
    sql = f"""
    SELECT
        ID_AUDITORIA,
        FECHA_EVENTO,
        USUARIO,
        OPERACION,
        ID_REGISTRO_ANTERIOR,
        ID_REGISTRO_NUEVO,
        CAMPO,
        VALOR_ANTERIOR,
        VALOR_NUEVO,
        OBSERVACION
    FROM {AUDIT_TABLE}
    WHERE ID_ESTABLECIMIENTO = ?
    ORDER BY ID_AUDITORIA DESC
    """

    conn = None
    try:
        conn = get_sqlserver_connection()
        cursor = conn.cursor()
        cursor.execute(sql, int(id_establecimiento))
        return _rows_to_dicts(cursor, cursor.fetchall())
    finally:
        if conn is not None:
            conn.close()


def obtener_redes():
    sql = f"""
    SELECT DISTINCT
        RED_ASISTENCIAL
    FROM {TABLE_NAME}
    WHERE ES_VERSION_ACTUAL = 1
      AND ES_OFICIAL = 1
      AND NULLIF(LTRIM(RTRIM(RED_ASISTENCIAL)), '') IS NOT NULL
    ORDER BY RED_ASISTENCIAL
    """

    conn = None
    try:
        conn = get_sqlserver_connection()
        cursor = conn.cursor()
        cursor.execute(sql)
        return [row[0] for row in cursor.fetchall()]
    finally:
        if conn is not None:
            conn.close()


def obtener_dataset_exportacion(
    universo="OFICIAL",
    condicion_centro=None,
    red_asistencial=None,
):
    universo = str(universo or "OFICIAL").strip().upper()

    where = []
    params = []

    if universo == "OFICIAL":
        where.extend([
            "ES_VERSION_ACTUAL = 1",
            "ES_OFICIAL = 1",
        ])
    elif universo == "MAESTRO_ACTUAL":
        where.append("ES_VERSION_ACTUAL = 1")
    elif universo == "HISTORICO":
        pass
    else:
        raise ValueError(
            "universo debe ser OFICIAL, MAESTRO_ACTUAL o HISTORICO."
        )

    if condicion_centro:
        where.append("CONDICION_CENTRO = ?")
        params.append(str(condicion_centro).strip().upper())

    if red_asistencial:
        where.append("RED_ASISTENCIAL = ?")
        params.append(str(red_asistencial).strip())

    where_sql = " AND ".join(where) if where else "1 = 1"

    sql = f"""
    SELECT
        ID_REGISTRO,
        ID_ESTABLECIMIENTO,
        COD_EESS,
        COD_SES,
        RENIPRESS,
        COD_RENIPRES_ANTERIOR,
        ID_REGISTRO_ANTERIOR,
        ES_VERSION_ACTUAL,
        FECHA_CAMBIO_RENIPRES,
        NOMBRE_ESTABLECIMIENTO,
        RED_ASISTENCIAL,
        RED_ABREVIADA,
        TIPO_ESSALUD,
        NIVEL_ESSALUD,
        TIPO_CENTRO,
        DESCRIPCION_TIPO,
        ESTADO_ESSALUD,
        ACTIVO_ESSALUD,
        DEPARTAMENTO,
        PROVINCIA,
        DISTRITO,
        UBIGEO,
        DIRECCION,
        CATEGORIA,
        TIPO_DOC_CATEGORIZACION,
        NRO_DOC_CATEGORIZACION,
        RESOLUCION_CATEGORIZACION_GCPS,
        INICIO_ACTIVIDAD,
        ESTADO_RENIPRESS,
        LATITUD,
        LONGITUD,
        CAMAS,
        NUMERO_RESOLUCION_ESSALUD,
        LINK_RESOLUCION,
        FUENTE_RENIPRESS,
        APROBADO_GCPS,
        CLASIFICACION_CONCILIACION,
        OBSERVACION,
        OBSERVACION_CONSOLIDACION,
        CONDICION_CENTRO,
        ES_OFICIAL,
        ENTIDAD_VALIDADORA
    FROM {TABLE_NAME}
    WHERE {where_sql}
    ORDER BY
        ES_VERSION_ACTUAL DESC,
        ES_OFICIAL DESC,
        RED_ASISTENCIAL,
        NOMBRE_ESTABLECIMIENTO,
        ID_REGISTRO DESC
    """

    conn = None
    try:
        conn = get_sqlserver_connection()
        cursor = conn.cursor()
        cursor.execute(sql, *params)
        return _rows_to_dicts(cursor, cursor.fetchall())
    finally:
        if conn is not None:
            conn.close()


def actualizar_establecimiento(
    id_registro,
    cambios,
    usuario,
    observacion=None,
):
    """
    UPDATE normal sobre una versión vigente.
    No permite modificar RENIPRESS ni campos técnicos de versionado.
    """
    id_registro = int(id_registro)
    usuario = str(usuario or "SISTEMA_SIEST").strip()[:150]

    requested = {
        k: v
        for k, v in (cambios or {}).items()
        if k in EDITABLE_FIELDS
    }

    if not requested:
        return []

    conn = None

    try:
        conn = get_sqlserver_connection()
        conn.autocommit = False
        cursor = conn.cursor()

        columns = sorted(requested.keys())
        select_cols = ", ".join(f"[{c}]" for c in columns)

        cursor.execute(
            f"""
            SELECT
                ID_ESTABLECIMIENTO,
                {select_cols}
            FROM {TABLE_NAME} WITH (UPDLOCK, HOLDLOCK)
            WHERE ID_REGISTRO = ?
              AND ES_VERSION_ACTUAL = 1
            """,
            id_registro,
        )

        row = cursor.fetchone()

        if not row:
            raise RuntimeError(
                "El registro no existe o ya no es la versión vigente."
            )

        current_columns = [
            col[0]
            for col in cursor.description
        ]
        current = dict(zip(current_columns, row))
        id_establecimiento = current["ID_ESTABLECIMIENTO"]

        real_changes = []

        for field in columns:
            old = current.get(field)
            new = requested[field]

            old_text = _audit_text(old)
            new_text = _audit_text(new)

            if (old_text or "") != (new_text or ""):
                real_changes.append(
                    {
                        "CAMPO": field,
                        "VALOR_ANTERIOR": old,
                        "VALOR_NUEVO": new,
                    }
                )

        if not real_changes:
            conn.rollback()
            return []

        update_values = {
            item["CAMPO"]: item["VALOR_NUEVO"]
            for item in real_changes
        }

        # Compatibilidad temporal con el campo legado.
        if "ES_OFICIAL" in update_values:
            official = int(update_values["ES_OFICIAL"] or 0)
            update_values["APROBADO_GCPS"] = "SI" if official == 1 else "NO"

        set_sql = ", ".join(
            f"[{field}] = ?"
            for field in update_values.keys()
        )

        params = list(update_values.values()) + [id_registro]

        cursor.execute(
            f"""
            UPDATE {TABLE_NAME}
               SET {set_sql}
             WHERE ID_REGISTRO = ?
               AND ES_VERSION_ACTUAL = 1
            """,
            *params,
        )

        if cursor.rowcount != 1:
            raise RuntimeError(
                "La actualización no afectó exactamente una fila."
            )

        for item in real_changes:
            cursor.execute(
                f"""
                INSERT INTO {AUDIT_TABLE}
                (
                    USUARIO,
                    OPERACION,
                    ID_ESTABLECIMIENTO,
                    ID_REGISTRO_ANTERIOR,
                    ID_REGISTRO_NUEVO,
                    CAMPO,
                    VALOR_ANTERIOR,
                    VALOR_NUEVO,
                    OBSERVACION
                )
                VALUES
                (?, 'UPDATE_DATOS', ?, ?, ?, ?, ?, ?, ?)
                """,
                usuario,
                id_establecimiento,
                id_registro,
                id_registro,
                item["CAMPO"],
                _audit_text(item["VALOR_ANTERIOR"]),
                _audit_text(item["VALOR_NUEVO"]),
                observacion,
            )

        conn.commit()
        return real_changes

    except Exception:
        if conn is not None:
            conn.rollback()
        raise

    finally:
        if conn is not None:
            conn.close()


def crear_version_renipress(
    id_registro,
    nuevo_renipress,
    usuario,
    observacion=None,
):
    id_registro = int(id_registro)
    nuevo_renipress = str(nuevo_renipress or "").strip()
    usuario = str(usuario or "SISTEMA_SIEST").strip()[:150]

    if not nuevo_renipress:
        raise ValueError("Debe ingresar el nuevo RENIPRESS.")

    conn = None

    try:
        conn = get_sqlserver_connection()
        conn.autocommit = False
        cursor = conn.cursor()

        cursor.execute(
            f"""
            SELECT
                ID_REGISTRO,
                ID_ESTABLECIMIENTO,
                RENIPRESS
            FROM {TABLE_NAME} WITH (UPDLOCK, HOLDLOCK)
            WHERE ID_REGISTRO = ?
              AND ES_VERSION_ACTUAL = 1
            """,
            id_registro,
        )

        current = cursor.fetchone()

        if not current:
            raise RuntimeError(
                "El registro no existe o ya no es la versión vigente."
            )

        old_id = int(current[0])
        id_establecimiento = int(current[1])
        old_renipress = current[2]

        if (old_renipress or "") == nuevo_renipress:
            raise ValueError(
                "El nuevo RENIPRESS es igual al RENIPRESS vigente."
            )

        cursor.execute(
            f"""
            SELECT TOP 1
                ID_REGISTRO,
                ID_ESTABLECIMIENTO,
                NOMBRE_ESTABLECIMIENTO
            FROM {TABLE_NAME} WITH (UPDLOCK, HOLDLOCK)
            WHERE ES_VERSION_ACTUAL = 1
              AND RENIPRESS = ?
              AND ID_ESTABLECIMIENTO <> ?
            """,
            nuevo_renipress,
            id_establecimiento,
        )

        duplicated = cursor.fetchone()

        if duplicated:
            raise ValueError(
                "El RENIPRESS ya está asignado a otro establecimiento "
                f"(ID_ESTABLECIMIENTO={duplicated[1]})."
            )

        cursor.execute(
            f"""
            UPDATE {TABLE_NAME}
               SET ES_VERSION_ACTUAL = 0
             WHERE ID_REGISTRO = ?
               AND ES_VERSION_ACTUAL = 1
            """,
            old_id,
        )

        if cursor.rowcount != 1:
            raise RuntimeError(
                "No fue posible cerrar la versión anterior."
            )

        cursor.execute(
            f"""
            INSERT INTO {TABLE_NAME}
            (
                ID_ESTABLECIMIENTO,
                COD_EESS,
                COD_SES,
                RENIPRESS,
                COD_RENIPRES_ANTERIOR,
                ID_REGISTRO_ANTERIOR,
                ES_VERSION_ACTUAL,
                FECHA_CAMBIO_RENIPRES,
                NOMBRE_ESTABLECIMIENTO,
                RED_ASISTENCIAL,
                RED_ABREVIADA,
                TIPO_ESSALUD,
                NIVEL_ESSALUD,
                TIPO_CENTRO,
                DESCRIPCION_TIPO,
                ESTADO_ESSALUD,
                ACTIVO_ESSALUD,
                DEPARTAMENTO,
                PROVINCIA,
                DISTRITO,
                UBIGEO,
                DIRECCION,
                CATEGORIA,
                TIPO_DOC_CATEGORIZACION,
                NRO_DOC_CATEGORIZACION,
                RESOLUCION_CATEGORIZACION_GCPS,
                INICIO_ACTIVIDAD,
                ESTADO_RENIPRESS,
                LATITUD,
                LONGITUD,
                CAMAS,
                NUMERO_RESOLUCION_ESSALUD,
                LINK_RESOLUCION,
                FUENTE_RENIPRESS,
                APROBADO_GCPS,
                CLASIFICACION_CONCILIACION,
                OBSERVACION,
                OBSERVACION_CONSOLIDACION,
                CONDICION_CENTRO,
                ES_OFICIAL,
                ENTIDAD_VALIDADORA
            )
            OUTPUT INSERTED.ID_REGISTRO
            SELECT
                ID_ESTABLECIMIENTO,
                COD_EESS,
                COD_SES,
                ?,
                RENIPRESS,
                ID_REGISTRO,
                1,
                GETDATE(),
                NOMBRE_ESTABLECIMIENTO,
                RED_ASISTENCIAL,
                RED_ABREVIADA,
                TIPO_ESSALUD,
                NIVEL_ESSALUD,
                TIPO_CENTRO,
                DESCRIPCION_TIPO,
                ESTADO_ESSALUD,
                ACTIVO_ESSALUD,
                DEPARTAMENTO,
                PROVINCIA,
                DISTRITO,
                UBIGEO,
                DIRECCION,
                CATEGORIA,
                TIPO_DOC_CATEGORIZACION,
                NRO_DOC_CATEGORIZACION,
                RESOLUCION_CATEGORIZACION_GCPS,
                INICIO_ACTIVIDAD,
                ESTADO_RENIPRESS,
                LATITUD,
                LONGITUD,
                CAMAS,
                NUMERO_RESOLUCION_ESSALUD,
                LINK_RESOLUCION,
                FUENTE_RENIPRESS,
                APROBADO_GCPS,
                CLASIFICACION_CONCILIACION,
                OBSERVACION,
                OBSERVACION_CONSOLIDACION,
                CONDICION_CENTRO,
                ES_OFICIAL,
                ENTIDAD_VALIDADORA
            FROM {TABLE_NAME}
            WHERE ID_REGISTRO = ?
            """,
            nuevo_renipress,
            old_id,
        )

        new_id = int(cursor.fetchone()[0])

        cursor.execute(
            f"""
            INSERT INTO {AUDIT_TABLE}
            (
                USUARIO,
                OPERACION,
                ID_ESTABLECIMIENTO,
                ID_REGISTRO_ANTERIOR,
                ID_REGISTRO_NUEVO,
                CAMPO,
                VALOR_ANTERIOR,
                VALOR_NUEVO,
                OBSERVACION
            )
            VALUES
            (?, 'CAMBIO_RENIPRESS', ?, ?, ?, 'RENIPRESS', ?, ?, ?)
            """,
            usuario,
            id_establecimiento,
            old_id,
            new_id,
            _audit_text(old_renipress),
            nuevo_renipress,
            observacion,
        )

        conn.commit()

        return {
            "ID_ESTABLECIMIENTO": id_establecimiento,
            "ID_REGISTRO_ANTERIOR": old_id,
            "ID_REGISTRO_NUEVO": new_id,
            "RENIPRESS_ANTERIOR": old_renipress,
            "RENIPRESS_NUEVO": nuevo_renipress,
        }

    except Exception:
        if conn is not None:
            conn.rollback()
        raise

    finally:
        if conn is not None:
            conn.close()


def obtener_centros_caracterizacion(
    condicion_centro=None,
    red_asistencial=None,
):
    """
    Dataset liviano para la pestaña Caracterización de Establecimientos.

    Universo:
        - versión vigente;
        - maestro oficial.

    Permite filtrar por condición EsSalud y red.
    """
    where = [
        "ES_VERSION_ACTUAL = 1",
        "ES_OFICIAL = 1",
    ]
    params = []

    if condicion_centro:
        where.append("CONDICION_CENTRO = ?")
        params.append(str(condicion_centro).strip().upper())

    if red_asistencial:
        where.append("RED_ASISTENCIAL = ?")
        params.append(str(red_asistencial).strip())

    sql = f"""
    SELECT
        ID_REGISTRO,
        ID_ESTABLECIMIENTO,
        COD_EESS,
        COD_SES,
        RENIPRESS,
        NOMBRE_ESTABLECIMIENTO,
        RED_ASISTENCIAL,
        NIVEL_ESSALUD,
        TIPO_CENTRO,
        CATEGORIA,
        CONDICION_CENTRO,
        ENTIDAD_VALIDADORA,
        ACTIVO_ESSALUD,
        DEPARTAMENTO,
        PROVINCIA,
        DISTRITO,
        UBIGEO
    FROM {TABLE_NAME}
    WHERE {" AND ".join(where)}
    ORDER BY
        CASE
            WHEN NIVEL_ESSALUD = 'NIVEL III' THEN 1
            WHEN NIVEL_ESSALUD = 'NIVEL II' THEN 2
            WHEN NIVEL_ESSALUD = 'NIVEL I' THEN 3
            ELSE 4
        END,
        CATEGORIA,
        NOMBRE_ESTABLECIMIENTO
    """

    conn = None

    try:
        conn = get_sqlserver_connection()
        cursor = conn.cursor()
        cursor.execute(sql, *params)
        return _rows_to_dicts(cursor, cursor.fetchall())

    finally:
        if conn is not None:
            conn.close()
