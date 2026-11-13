from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO
import re
from pathlib import Path

import pandas as pd

SERVICE_VERSION = "2026-11-04-COMPARISONFIX-V2"

from backend.establecimientos_repository_v3 import (
    obtener_calidad_maestro,
    obtener_dataset_exportacion,
    obtener_distribucion,
    obtener_resumen_ejecutivo,
)


FIELD_DEFINITIONS = [
    {
        "field": "COD_EESS",
        "label": "Código EESS",
        "group": "Identificación",
        "type": "text",
    },
    {
        "field": "COD_SES",
        "label": "Código SES",
        "group": "Identificación",
        "type": "text",
    },
    {
        "field": "NOMBRE_ESTABLECIMIENTO",
        "label": "Nombre del establecimiento",
        "group": "Identificación",
        "type": "text",
        "width": 12,
    },
    {
        "field": "CONDICION_CENTRO",
        "label": "Condición EsSalud",
        "group": "Identificación",
        "type": "select",
        "options": ["PROPIO", "EXTRA"],
    },
    {
        "field": "ES_OFICIAL",
        "label": "Pertenece al maestro oficial",
        "group": "Identificación",
        "type": "boolean",
    },
    {
        "field": "ENTIDAD_VALIDADORA",
        "label": "Entidad validadora",
        "group": "Identificación",
        "type": "select",
        "options": ["GCPS", "GCOP/OPERACIONES"],
    },

    {
        "field": "RED_ASISTENCIAL",
        "label": "Red asistencial",
        "group": "Información EsSalud",
        "type": "text",
        "width": 8,
    },
    {
        "field": "RED_ABREVIADA",
        "label": "Red abreviada",
        "group": "Información EsSalud",
        "type": "text",
    },
    {
        "field": "TIPO_ESSALUD",
        "label": "Tipo EsSalud",
        "group": "Información EsSalud",
        "type": "text",
    },
    {
        "field": "NIVEL_ESSALUD",
        "label": "Nivel EsSalud",
        "group": "Información EsSalud",
        "type": "text",
    },
    {
        "field": "TIPO_CENTRO",
        "label": "Tipo de centro",
        "group": "Información EsSalud",
        "type": "text",
    },
    {
        "field": "DESCRIPCION_TIPO",
        "label": "Descripción del tipo",
        "group": "Información EsSalud",
        "type": "text",
        "width": 8,
    },
    {
        "field": "ESTADO_ESSALUD",
        "label": "Estado EsSalud",
        "group": "Información EsSalud",
        "type": "text",
    },
    {
        "field": "ACTIVO_ESSALUD",
        "label": "Activo EsSalud",
        "group": "Información EsSalud",
        "type": "boolean",
    },

    {
        "field": "DEPARTAMENTO",
        "label": "Departamento",
        "group": "RENIPRESS y ubicación",
        "type": "text",
    },
    {
        "field": "PROVINCIA",
        "label": "Provincia",
        "group": "RENIPRESS y ubicación",
        "type": "text",
    },
    {
        "field": "DISTRITO",
        "label": "Distrito",
        "group": "RENIPRESS y ubicación",
        "type": "text",
    },
    {
        "field": "UBIGEO",
        "label": "UBIGEO",
        "group": "RENIPRESS y ubicación",
        "type": "text",
    },
    {
        "field": "DIRECCION",
        "label": "Dirección",
        "group": "RENIPRESS y ubicación",
        "type": "textarea",
        "width": 12,
    },
    {
        "field": "CATEGORIA",
        "label": "Categoría",
        "group": "RENIPRESS y ubicación",
        "type": "text",
    },
    {
        "field": "TIPO_DOC_CATEGORIZACION",
        "label": "Tipo doc. categorización",
        "group": "RENIPRESS y ubicación",
        "type": "text",
    },
    {
        "field": "NRO_DOC_CATEGORIZACION",
        "label": "Nro. doc. categorización",
        "group": "RENIPRESS y ubicación",
        "type": "text",
    },
    {
        "field": "RESOLUCION_CATEGORIZACION_GCPS",
        "label": "Resolución de categorización",
        "group": "RENIPRESS y ubicación",
        "type": "textarea",
        "width": 8,
    },
    {
        "field": "INICIO_ACTIVIDAD",
        "label": "Inicio de actividad",
        "group": "RENIPRESS y ubicación",
        "type": "date",
    },
    {
        "field": "ESTADO_RENIPRESS",
        "label": "Estado RENIPRESS",
        "group": "RENIPRESS y ubicación",
        "type": "text",
    },

    {
        "field": "LATITUD",
        "label": "Latitud",
        "group": "Capacidad y documentación",
        "type": "decimal",
    },
    {
        "field": "LONGITUD",
        "label": "Longitud",
        "group": "Capacidad y documentación",
        "type": "decimal",
    },
    {
        "field": "CAMAS",
        "label": "Camas",
        "group": "Capacidad y documentación",
        "type": "integer",
    },
    {
        "field": "NUMERO_RESOLUCION_ESSALUD",
        "label": "Resolución EsSalud",
        "group": "Capacidad y documentación",
        "type": "text",
        "width": 8,
    },
    {
        "field": "LINK_RESOLUCION",
        "label": "Enlace de resolución",
        "group": "Capacidad y documentación",
        "type": "textarea",
        "width": 12,
    },
    {
        "field": "FUENTE_RENIPRESS",
        "label": "Fuente RENIPRESS",
        "group": "Capacidad y documentación",
        "type": "text",
    },
    {
        "field": "OBSERVACION",
        "label": "Observación",
        "group": "Observaciones",
        "type": "textarea",
        "width": 12,
    },
    {
        "field": "OBSERVACION_CONSOLIDACION",
        "label": "Observación de consolidación",
        "group": "Observaciones",
        "type": "textarea",
        "width": 12,
    },
]


FIELD_MAP = {
    item["field"]: item
    for item in FIELD_DEFINITIONS
}


def _null_if_blank(value):
    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    return text


def _uppercase(value):
    value = _null_if_blank(value)
    if value is None:
        return None
    return value.upper()


def normalizar_renipress(value):
    value = _null_if_blank(value)

    if value is None:
        raise ValueError("Debe ingresar un RENIPRESS.")

    if value.endswith(".0") and value[:-2].isdigit():
        value = value[:-2]

    if value.isdigit():
        value = value.zfill(8)

    if len(value) > 20:
        raise ValueError("El RENIPRESS supera los 20 caracteres.")

    return value.upper()


def normalizar_campo(field, value):
    definition = FIELD_MAP[field]
    field_type = definition["type"]

    if field == "LINK_RESOLUCION":
        return _null_if_blank(value)

    if field == "UBIGEO":
        value = _uppercase(value)
        if value and value.isdigit():
            return value.zfill(6)
        return value

    if field_type in {"text", "textarea", "select"}:
        return _uppercase(value)

    if field_type == "boolean":
        if value in (None, ""):
            return None
        if value in (True, 1, "1", "SI", "SÍ", "TRUE"):
            return 1
        if value in (False, 0, "0", "NO", "FALSE"):
            return 0
        raise ValueError(
            f"{definition['label']}: valor booleano no válido."
        )

    if field_type == "integer":
        if value in (None, ""):
            return None
        try:
            number = float(value)
        except (TypeError, ValueError):
            raise ValueError(
                f"{definition['label']}: debe ser un número entero."
            )
        if not number.is_integer():
            raise ValueError(
                f"{definition['label']}: debe ser un número entero."
            )
        result = int(number)
        if field == "CAMAS" and result < 0:
            raise ValueError("Camas no puede ser negativo.")
        return result

    if field_type == "decimal":
        if value in (None, ""):
            return None
        try:
            result = float(str(value).replace(",", "."))
        except (TypeError, ValueError):
            raise ValueError(
                f"{definition['label']}: valor decimal no válido."
            )

        if field == "LATITUD" and not (-90 <= result <= 90):
            raise ValueError("Latitud debe estar entre -90 y 90.")

        if field == "LONGITUD" and not (-180 <= result <= 180):
            raise ValueError("Longitud debe estar entre -180 y 180.")

        return result

    if field_type == "date":
        if value in (None, ""):
            return None

        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d")

        if isinstance(value, date):
            return value.strftime("%Y-%m-%d")

        text_value = str(value).strip()

        # Los input type="date" devuelven YYYY-MM-DD.
        # Ese formato debe interpretarse estrictamente como ISO.
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text_value):
            try:
                parsed = datetime.strptime(
                    text_value,
                    "%Y-%m-%d",
                )
                return parsed.strftime("%Y-%m-%d")
            except ValueError:
                raise ValueError(
                    f"{definition['label']}: fecha no válida."
                )

        # Para formatos como DD/MM/YYYY.
        parsed = pd.to_datetime(
            text_value,
            errors="coerce",
            dayfirst=True,
        )

        if pd.isna(parsed):
            raise ValueError(
                f"{definition['label']}: fecha no válida."
            )

        return parsed.strftime("%Y-%m-%d")

    raise ValueError(f"Tipo de campo no soportado: {field_type}")


def preparar_cambios_edicion(original, form_values):
    """
    form_values:
        dict {field: value}

    Devuelve:
        cambios normalizados
        diferencias listas para presentación
    """
    normalized = {}

    for definition in FIELD_DEFINITIONS:
        field = definition["field"]
        normalized[field] = normalizar_campo(
            field,
            form_values.get(field),
        )

    # Reglas semánticas de oficialidad.
    official = normalized.get("ES_OFICIAL")
    condition = normalized.get("CONDICION_CENTRO")

    if official == 1:
        if condition == "PROPIO":
            normalized["ENTIDAD_VALIDADORA"] = "GCPS"
        elif condition == "EXTRA":
            normalized["ENTIDAD_VALIDADORA"] = "GCOP/OPERACIONES"
    elif official == 0:
        normalized["ENTIDAD_VALIDADORA"] = None

    changes = {}
    differences = []

    for definition in FIELD_DEFINITIONS:
        field = definition["field"]
        new = normalized.get(field)
        old = original.get(field)

        old_cmp = _comparison_value(field, old)
        new_cmp = _comparison_value(field, new)

        if old_cmp != new_cmp:
            changes[field] = new

            differences.append(
                {
                    "CAMPO": definition["label"],
                    "CAMPO_TECNICO": field,
                    "VALOR_ANTERIOR": _display_value(old),
                    "VALOR_NUEVO": _display_value(new),
                }
            )

    return changes, differences


def _comparison_value(field, value):
    """
    Compara valores por significado y no por representación textual.

    Evita falsos positivos como:
      - 10/02/1994 vs 1994-02-10
      - -16.39482280 vs -16.3948228
      - True vs 1 vs "SI"
      - 3 vs 3.0 vs "3"
    """
    if value is None:
        return None

    definition = FIELD_MAP.get(field, {})
    field_type = definition.get("type")

    if isinstance(value, str) and not value.strip():
        return None

    if field_type == "date":
        if isinstance(value, datetime):
            return value.date().isoformat()

        if isinstance(value, date):
            return value.isoformat()

        text_value = str(value).strip()

        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text_value):
            try:
                return datetime.strptime(
                    text_value,
                    "%Y-%m-%d",
                ).date().isoformat()
            except ValueError:
                return text_value

        parsed = pd.to_datetime(
            text_value,
            errors="coerce",
            dayfirst=True,
        )

        if pd.isna(parsed):
            return text_value

        return parsed.date().isoformat()

    if field_type == "decimal":
        try:
            dec = Decimal(
                str(value).strip().replace(",", ".")
            )
            return dec.quantize(
                Decimal("0.00000001")
            )
        except (InvalidOperation, ValueError):
            return str(value).strip()

    if field_type == "integer":
        try:
            return int(
                Decimal(str(value).strip())
            )
        except (InvalidOperation, ValueError):
            return str(value).strip()

    if field_type == "boolean":
        if value in (
            True,
            1,
            "1",
            "SI",
            "SÍ",
            "TRUE",
            "VERDADERO",
        ):
            return 1

        if value in (
            False,
            0,
            "0",
            "NO",
            "FALSE",
            "FALSO",
        ):
            return 0

        return str(value).strip().upper()

    return str(value).strip()


def _display_value(value):
    if value is None or str(value).strip() == "":
        return "-"

    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y %H:%M:%S")

    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")

    if value is True:
        return "SI"

    if value is False:
        return "NO"

    return str(value)


def dataset_a_dataframe(records):
    df = pd.DataFrame(records)

    if df.empty:
        return df

    for column in [
        "ES_VERSION_ACTUAL",
        "ACTIVO_ESSALUD",
        "ES_OFICIAL",
    ]:
        if column in df.columns:
            df[column] = df[column].map(
                lambda x: (
                    "SI"
                    if x in (1, True, "1")
                    else (
                        "NO"
                        if x in (0, False, "0")
                        else None
                    )
                )
            )

    return df


def generar_excel_maestro(
    universo="OFICIAL",
    condicion_centro=None,
    red_asistencial=None,
):
    records = obtener_dataset_exportacion(
        universo=universo,
        condicion_centro=condicion_centro,
        red_asistencial=red_asistencial,
    )

    df = dataset_a_dataframe(records)

    buffer = BytesIO()

    with pd.ExcelWriter(
        buffer,
        engine="openpyxl",
    ) as writer:
        df.to_excel(
            writer,
            index=False,
            sheet_name="ESTABLECIMIENTOS",
        )

        ws = writer.book["ESTABLECIMIENTOS"]
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions

        for cell in ws[1]:
            cell.font = cell.font.copy(
                bold=True,
                color="FFFFFF",
            )
            cell.fill = cell.fill.copy(
                fill_type="solid",
                fgColor="1F4E78",
            )

        for column_cells in ws.columns:
            max_length = 0
            letter = column_cells[0].column_letter

            for cell in column_cells[:1000]:
                value = "" if cell.value is None else str(cell.value)
                max_length = max(max_length, len(value))

            ws.column_dimensions[letter].width = min(
                max(max_length + 2, 10),
                45,
            )

    buffer.seek(0)
    return buffer.getvalue(), len(df)


def generar_csv_maestro(
    universo="OFICIAL",
    condicion_centro=None,
    red_asistencial=None,
):
    records = obtener_dataset_exportacion(
        universo=universo,
        condicion_centro=condicion_centro,
        red_asistencial=red_asistencial,
    )

    df = dataset_a_dataframe(records)

    content = df.to_csv(
        index=False,
        sep=";",
        encoding="utf-8-sig",
    )

    return content, len(df)


def generar_excel_resumen_ejecutivo():
    resumen = obtener_resumen_ejecutivo()
    calidad = obtener_calidad_maestro()

    redes = pd.DataFrame(
        obtener_distribucion("RED_ASISTENCIAL", top=100)
    )

    niveles = pd.DataFrame(
        obtener_distribucion("NIVEL_ESSALUD", top=100)
    )

    categorias = pd.DataFrame(
        obtener_distribucion("CATEGORIA", top=100)
    )

    departamentos = pd.DataFrame(
        obtener_distribucion("DEPARTAMENTO", top=100)
    )

    total = int(calidad.get("TOTAL") or 0)

    quality_rows = []

    quality_definitions = [
        ("RENIPRESS", "CON_RENIPRESS"),
        ("UBIGEO", "CON_UBIGEO"),
        ("COORDENADAS", "CON_COORDENADAS"),
        ("CATEGORÍA", "CON_CATEGORIA"),
        ("RESOLUCIÓN", "CON_RESOLUCION"),
        ("DIRECCIÓN", "CON_DIRECCION"),
        ("RED ASISTENCIAL", "CON_RED"),
        ("NIVEL ESSALUD", "CON_NIVEL"),
    ]

    for label, key in quality_definitions:
        count = int(calidad.get(key) or 0)
        pct = round((count * 100 / total), 2) if total else 0

        quality_rows.append(
            {
                "INDICADOR": label,
                "COMPLETOS": count,
                "TOTAL": total,
                "PORCENTAJE": pct,
                "PENDIENTES": max(total - count, 0),
            }
        )

    calidad_df = pd.DataFrame(quality_rows)

    resumen_df = pd.DataFrame(
        [
            {
                "INDICADOR": "Centros oficiales",
                "VALOR": resumen.get("TOTAL_OFICIALES", 0),
            },
            {
                "INDICADOR": "Centros propios oficiales",
                "VALOR": resumen.get("TOTAL_PROPIOS", 0),
            },
            {
                "INDICADOR": "Centros extra oficiales",
                "VALOR": resumen.get("TOTAL_EXTRAS", 0),
            },
            {
                "INDICADOR": "Fuera del maestro oficial",
                "VALOR": resumen.get("TOTAL_FUERA_OFICIAL", 0),
            },
            {
                "INDICADOR": "Versiones históricas generadas",
                "VALOR": resumen.get("TOTAL_VERSIONES_HISTORICAS", 0),
            },
            {
                "INDICADOR": "Centros operativos oficiales",
                "VALOR": resumen.get("TOTAL_OPERATIVOS", 0),
            },
        ]
    )

    buffer = BytesIO()

    with pd.ExcelWriter(
        buffer,
        engine="openpyxl",
    ) as writer:
        resumen_df.to_excel(
            writer,
            index=False,
            sheet_name="RESUMEN",
        )
        redes.to_excel(
            writer,
            index=False,
            sheet_name="POR_RED",
        )
        niveles.to_excel(
            writer,
            index=False,
            sheet_name="POR_NIVEL",
        )
        categorias.to_excel(
            writer,
            index=False,
            sheet_name="POR_CATEGORIA",
        )
        departamentos.to_excel(
            writer,
            index=False,
            sheet_name="POR_DEPARTAMENTO",
        )
        calidad_df.to_excel(
            writer,
            index=False,
            sheet_name="CALIDAD_DATOS",
        )

        for ws in writer.book.worksheets:
            ws.freeze_panes = "A2"
            ws.auto_filter.ref = ws.dimensions

            for cell in ws[1]:
                cell.font = cell.font.copy(
                    bold=True,
                    color="FFFFFF",
                )
                cell.fill = cell.fill.copy(
                    fill_type="solid",
                    fgColor="1F4E78",
                )

            for column_cells in ws.columns:
                max_length = 0
                letter = column_cells[0].column_letter

                for cell in column_cells[:1000]:
                    value = "" if cell.value is None else str(cell.value)
                    max_length = max(max_length, len(value))

                ws.column_dimensions[letter].width = min(
                    max(max_length + 2, 12),
                    40,
                )

    buffer.seek(0)
    return buffer.getvalue()


CHAR_LEVEL_ORDER = [
    "NIVEL I",
    "NIVEL II",
    "NIVEL III",
    "SIN NIVEL",
]


def normalizar_nivel_caracterizacion(value):
    """
    Lleva NIVEL_ESSALUD a cuatro grupos ejecutivos:
    NIVEL I, NIVEL II, NIVEL III y SIN NIVEL.
    """
    if value is None:
        return "SIN NIVEL"

    text = str(value).strip().upper()

    if not text:
        return "SIN NIVEL"

    aliases = {
        "I": "NIVEL I",
        "1": "NIVEL I",
        "NIVEL 1": "NIVEL I",
        "NIVEL I": "NIVEL I",

        "II": "NIVEL II",
        "2": "NIVEL II",
        "NIVEL 2": "NIVEL II",
        "NIVEL II": "NIVEL II",

        "III": "NIVEL III",
        "3": "NIVEL III",
        "NIVEL 3": "NIVEL III",
        "NIVEL III": "NIVEL III",
    }

    return aliases.get(text, "SIN NIVEL")


def normalizar_categoria_caracterizacion(value):
    if value is None:
        return "SIN CATEGORÍA"

    text = str(value).strip().upper()

    if not text:
        return "SIN CATEGORÍA"

    if text in {
        "SIN CATEGORIA",
        "SIN CATEGORÍA",
        "S/C",
        "NO APLICA",
    }:
        return "SIN CATEGORÍA"

    return text


def construir_caracterizacion_establecimientos(records):
    """
    Agrega el dataset oficial para la nueva pestaña de caracterización.

    Devuelve una estructura preparada para:
      - tarjetas institucionales;
      - popovers por nivel/condición;
      - jerarquía Nivel -> Categoría MINSA -> Centro;
      - distribución por tipo de centro;
      - distribución por red.
    """
    records = records or []

    levels = {
        level: {
            "count": 0,
            "categories": defaultdict(list),
            "centers": [],
        }
        for level in CHAR_LEVEL_ORDER
    }

    condition_counts = Counter()
    condition_levels = {
        "PROPIO": Counter(),
        "EXTRA": Counter(),
    }

    type_counts = Counter()
    red_counts = Counter()

    centers_by_condition_level = {
        "PROPIO": defaultdict(list),
        "EXTRA": defaultdict(list),
    }

    normalized_records = []

    for row in records:
        level = normalizar_nivel_caracterizacion(
            row.get("NIVEL_ESSALUD")
        )
        category = normalizar_categoria_caracterizacion(
            row.get("CATEGORIA")
        )

        condition = (
            str(row.get("CONDICION_CENTRO") or "")
            .strip()
            .upper()
        )

        if condition not in {"PROPIO", "EXTRA"}:
            condition = condition or "SIN CONDICIÓN"

        center_type = (
            str(row.get("TIPO_CENTRO") or "")
            .strip()
            .upper()
        ) or "SIN TIPO"

        network = (
            str(row.get("RED_ASISTENCIAL") or "")
            .strip()
        ) or "SIN RED"

        name = (
            str(row.get("NOMBRE_ESTABLECIMIENTO") or "")
            .strip()
        ) or "SIN NOMBRE"

        center = {
            "ID_REGISTRO": row.get("ID_REGISTRO"),
            "COD_EESS": row.get("COD_EESS"),
            "COD_SES": row.get("COD_SES"),
            "RENIPRESS": row.get("RENIPRESS"),
            "NOMBRE_ESTABLECIMIENTO": name,
            "RED_ASISTENCIAL": network,
            "NIVEL": level,
            "CATEGORIA": category,
            "TIPO_CENTRO": center_type,
            "CONDICION_CENTRO": condition,
            "ENTIDAD_VALIDADORA": row.get("ENTIDAD_VALIDADORA"),
            "DEPARTAMENTO": row.get("DEPARTAMENTO"),
            "PROVINCIA": row.get("PROVINCIA"),
            "DISTRITO": row.get("DISTRITO"),
            "UBIGEO": row.get("UBIGEO"),
        }

        normalized_records.append(center)

        levels[level]["count"] += 1
        levels[level]["categories"][category].append(center)
        levels[level]["centers"].append(center)

        condition_counts[condition] += 1

        if condition in condition_levels:
            condition_levels[condition][level] += 1
            centers_by_condition_level[condition][level].append(
                center
            )

        type_counts[center_type] += 1
        red_counts[network] += 1

    # Convertir defaultdict a dict normal y ordenar centros.
    for level in CHAR_LEVEL_ORDER:
        categories = levels[level]["categories"]

        ordered_categories = {}

        for category in sorted(
            categories.keys(),
            key=lambda x: (
                x == "SIN CATEGORÍA",
                x,
            ),
        ):
            ordered_categories[category] = sorted(
                categories[category],
                key=lambda x: x["NOMBRE_ESTABLECIMIENTO"],
            )

        levels[level]["categories"] = ordered_categories
        levels[level]["centers"] = sorted(
            levels[level]["centers"],
            key=lambda x: x["NOMBRE_ESTABLECIMIENTO"],
        )

    for condition in centers_by_condition_level:
        for level in list(
            centers_by_condition_level[condition].keys()
        ):
            centers_by_condition_level[condition][level] = sorted(
                centers_by_condition_level[condition][level],
                key=lambda x: x["NOMBRE_ESTABLECIMIENTO"],
            )

    return {
        "total": len(records),
        "condition_counts": dict(condition_counts),
        "condition_levels": {
            key: dict(value)
            for key, value in condition_levels.items()
        },
        "centers_by_condition_level": {
            condition: dict(level_map)
            for condition, level_map
            in centers_by_condition_level.items()
        },
        "levels": levels,
        "type_counts": dict(
            sorted(
                type_counts.items(),
                key=lambda item: (-item[1], item[0]),
            )
        ),
        "red_counts": dict(
            sorted(
                red_counts.items(),
                key=lambda item: (-item[1], item[0]),
            )
        ),
        "records": normalized_records,
    }
