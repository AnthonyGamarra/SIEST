from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO
import re
from pathlib import Path

import pandas as pd

SERVICE_VERSION = "2026-11-13-CARACTERIZACION-ESTRATEGICA-V4"

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


def _format_level_label(value):
    """Formato institucional de niveles con romanos en mayúscula."""
    text = str(value or "").strip().upper()

    labels = {
        "NIVEL I": "Nivel I",
        "NIVEL II": "Nivel II",
        "NIVEL III": "Nivel III",
        "SIN NIVEL": "Sin nivel",
    }

    return labels.get(text, str(value or "").strip())


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
    department_counts = Counter()
    category_counts = Counter()
    red_level_counts = defaultdict(Counter)

    alerts = {
        "SIN_NIVEL": 0,
        "SIN_CATEGORIA": 0,
        "SIN_TIPO": 0,
    }

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

        department = (
            str(row.get("DEPARTAMENTO") or "")
            .strip()
            .upper()
        ) or "SIN DEPARTAMENTO"

        department_counts[department] += 1
        category_counts[category] += 1
        red_level_counts[network][level] += 1

        if level == "SIN NIVEL":
            alerts["SIN_NIVEL"] += 1

        if category == "SIN CATEGORÍA":
            alerts["SIN_CATEGORIA"] += 1

        if center_type == "SIN TIPO":
            alerts["SIN_TIPO"] += 1

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
        "department_counts": dict(
            sorted(
                department_counts.items(),
                key=lambda item: (-item[1], item[0]),
            )
        ),
        "category_counts": dict(
            sorted(
                category_counts.items(),
                key=lambda item: (-item[1], item[0]),
            )
        ),
        "red_level_counts": {
            network: {
                level: int(level_counter.get(level, 0))
                for level in CHAR_LEVEL_ORDER
            }
            for network, level_counter
            in sorted(
                red_level_counts.items(),
                key=lambda item: (
                    -sum(item[1].values()),
                    item[0],
                ),
            )
        },
        "alerts": alerts,
        "records": normalized_records,
    }


def fuente_caracterizacion_por_condicion(condicion):
    """
    Fuente funcional solicitada para la caracterización.

    PROPIO -> GCPS
    EXTRA  -> GCOP
    TODOS  -> GCPS / GCOP
    """
    condicion = str(condicion or "").strip().upper()

    if condicion == "PROPIO":
        return "GCPS"

    if condicion == "EXTRA":
        return "GCOP"

    return "GCPS / GCOP"


def generar_excel_caracterizacion_establecimientos(
    records,
    condicion=None,
    red_asistencial=None,
):
    """
    Genera un boletín ejecutivo institucional en Excel.

    Hojas visibles:
        1. BOLETIN_EJECUTIVO
        2. DETALLE_CENTROS

    Hoja oculta:
        3. DATOS_GRAFICOS

    Mantiene la firma anterior para no requerir cambios en el callback
    de Dash. Devuelve:
        (bytes_xlsx, total_registros)
    """
    # Imports locales: el resto del servicio permanece desacoplado
    # de la construcción visual del boletín.
    from openpyxl import Workbook
    from openpyxl.chart import BarChart, PieChart, Reference
    from openpyxl.chart.label import DataLabelList
    from openpyxl.styles import (
        Alignment,
        Border,
        Font,
        PatternFill,
        Side,
    )
    from openpyxl.worksheet.table import Table, TableStyleInfo

    summary = construir_caracterizacion_establecimientos(
        records
    )

    fuente = fuente_caracterizacion_por_condicion(
        condicion
    )

    condition_value = str(
        condicion or ""
    ).strip().upper()

    condicion_label = (
        "OFERTA PROPIA"
        if condition_value == "PROPIO"
        else (
            "OFERTA EXTRAINSTITUCIONAL"
            if condition_value == "EXTRA"
            else "TODOS"
        )
    )

    red_label = (
        str(red_asistencial).strip()
        if red_asistencial
        else "TODAS"
    )

    total = int(summary.get("total") or 0)

    condition_counts = summary.get(
        "condition_counts",
        {},
    )

    own = int(
        condition_counts.get("PROPIO") or 0
    )

    extra = int(
        condition_counts.get("EXTRA") or 0
    )

    levels = summary.get("levels", {})
    alerts = summary.get("alerts", {})

    level_counts = {
        level: int(
            levels.get(level, {}).get("count") or 0
        )
        for level in CHAR_LEVEL_ORDER
    }

    # -----------------------------------------------------------------
    # Lectura gerencial automática
    # -----------------------------------------------------------------

    pct_own = (
        round(own * 100 / total, 1)
        if total else 0
    )

    pct_extra = (
        round(extra * 100 / total, 1)
        if total else 0
    )

    dominant_level = max(
        CHAR_LEVEL_ORDER,
        key=lambda level: level_counts.get(
            level,
            0,
        ),
    )

    dominant_level_count = level_counts.get(
        dominant_level,
        0,
    )

    dominant_level_pct = (
        round(
            dominant_level_count * 100 / total,
            1,
        )
        if total else 0
    )

    red_counts = summary.get(
        "red_counts",
        {},
    )

    top_red = (
        next(iter(red_counts.items()))
        if red_counts
        else ("SIN INFORMACIÓN", 0)
    )

    department_counts = summary.get(
        "department_counts",
        {},
    )

    top_department = (
        next(
            iter(
                department_counts.items()
            )
        )
        if department_counts
        else ("SIN INFORMACIÓN", 0)
    )

    sin_nivel = int(
        alerts.get("SIN_NIVEL") or 0
    )

    sin_categoria = int(
        alerts.get("SIN_CATEGORIA") or 0
    )

    sin_tipo = int(
        alerts.get("SIN_TIPO") or 0
    )

    lectura_1 = (
        f"La oferta analizada comprende {total} "
        f"establecimiento(s). La oferta propia representa "
        f"{pct_own:.1f}% ({own}) y la oferta "
        f"extrainstitucional {pct_extra:.1f}% ({extra})."
    )

    lectura_2 = (
        f"{_format_level_label(dominant_level) if dominant_level != 'SIN NIVEL' else 'Sin nivel'} "
        f"concentra la mayor cantidad de centros: "
        f"{dominant_level_count} ({dominant_level_pct:.1f}%). "
        f"La red con mayor oferta es {top_red[0]} "
        f"con {top_red[1]} establecimiento(s)."
    )

    if (
        sin_nivel
        or sin_categoria
        or sin_tipo
    ):
        lectura_3 = (
            "Como alertas de caracterización se identifican "
            f"{sin_nivel} centro(s) sin nivel, "
            f"{sin_categoria} sin categoría MINSA y "
            f"{sin_tipo} sin tipo de establecimiento. "
            "Estos registros deben formar parte del control "
            "de calidad del maestro institucional."
        )
    else:
        lectura_3 = (
            "No se identifican pendientes de nivel, categoría "
            "MINSA ni tipo de establecimiento en el universo "
            "seleccionado."
        )

    # -----------------------------------------------------------------
    # Workbook
    # -----------------------------------------------------------------

    wb = Workbook()

    ws = wb.active
    ws.title = "BOLETIN_EJECUTIVO"

    ws_detail = wb.create_sheet(
        "DETALLE_CENTROS"
    )

    ws_data = wb.create_sheet(
        "DATOS_GRAFICOS"
    )

    ws_data.sheet_state = "hidden"

    wb.properties.title = (
        "Caracterización de Establecimientos de Salud"
    )

    wb.properties.subject = (
        "Boletín ejecutivo SIEST"
    )

    wb.properties.creator = (
        "EsSalud - GCPP / GGI / SGE - SIEST"
    )

    # -----------------------------------------------------------------
    # Paleta institucional
    # -----------------------------------------------------------------

    C_BLUE = "005EA8"
    C_DARK = "17365D"
    C_SOFT = "EAF3F9"
    C_BG = "F4F7FA"
    C_BORDER = "DDE4EC"
    C_TEXT = "172033"
    C_MUTED = "687386"
    C_GREEN = "198754"
    C_ORANGE = "E67E22"
    C_YELLOW = "F4B400"
    C_LIGHT_GREEN = "EAF7F0"
    C_LIGHT_ORANGE = "FFF4EC"
    C_LIGHT_YELLOW = "FFF9E8"
    C_WHITE = "FFFFFF"

    thin = Side(
        style="thin",
        color=C_BORDER,
    )

    border = Border(
        left=thin,
        right=thin,
        top=thin,
        bottom=thin,
    )

    # -----------------------------------------------------------------
    # Configuración general de BOLETIN_EJECUTIVO
    # -----------------------------------------------------------------

    ws.sheet_view.showGridLines = False

    widths = {
        "A": 11,
        "B": 11,
        "C": 11,
        "D": 11,
        "E": 11,
        "F": 11,
        "G": 11,
        "H": 11,
        "I": 11,
        "J": 11,
        "K": 11,
        "L": 11,
        "M": 11,
        "N": 11,
    }

    for col, width in widths.items():
        ws.column_dimensions[col].width = width

    for row in range(1, 64):
        ws.row_dimensions[row].height = 19

    ws.row_dimensions[1].height = 30
    ws.row_dimensions[2].height = 25
    ws.row_dimensions[5].height = 28
    ws.row_dimensions[6].height = 28

    # Impresión tipo boletín.
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 1
    ws.print_area = "A1:N62"
    ws.freeze_panes = "A8"

    ws.oddFooter.left.text = (
        f"Fuente: {fuente}"
    )

    ws.oddFooter.center.text = (
        "Elaboración: GCPP - GGI - SGE"
    )

    ws.oddFooter.right.text = (
        "Página &P de &N"
    )

    # -----------------------------------------------------------------
    # Cabecera institucional
    # -----------------------------------------------------------------

    ws.merge_cells("A1:N2")
    ws["A1"] = "EsSalud  |  SIEST"
    ws["A1"].font = Font(
        name="Arial",
        size=20,
        bold=True,
        color=C_WHITE,
    )
    ws["A1"].fill = PatternFill(
        "solid",
        fgColor=C_BLUE,
    )
    ws["A1"].alignment = Alignment(
        horizontal="left",
        vertical="center",
    )

    for row in ws["A1:N2"]:
        for cell in row:
            cell.fill = PatternFill(
                "solid",
                fgColor=C_BLUE,
            )

    ws.merge_cells("A3:N3")
    ws["A3"] = (
        "GERENCIA CENTRAL DE PLANEAMIENTO Y PRESUPUESTO  ·  "
        "GERENCIA DE GESTIÓN DE LA INFORMACIÓN  ·  "
        "SUB GERENCIA DE ESTADÍSTICA"
    )
    ws["A3"].font = Font(
        name="Arial",
        size=9,
        bold=True,
        color=C_DARK,
    )
    ws["A3"].fill = PatternFill(
        "solid",
        fgColor=C_SOFT,
    )
    ws["A3"].alignment = Alignment(
        horizontal="center",
        vertical="center",
    )

    ws.merge_cells("A5:N6")
    ws["A5"] = (
        "CARACTERIZACIÓN DE ESTABLECIMIENTOS DE SALUD\n"
        "Maestro institucional de centros oficiales vigentes"
    )
    ws["A5"].font = Font(
        name="Arial",
        size=18,
        bold=True,
        color=C_TEXT,
    )
    ws["A5"].alignment = Alignment(
        horizontal="center",
        vertical="center",
        wrap_text=True,
    )

    # Filtros / fuente / fecha.
    filter_blocks = [
        (
            "A7:E7",
            f"CONDICIÓN ESSALUD: {condicion_label}",
        ),
        (
            "F7:I7",
            f"FUENTE: {fuente}",
        ),
        (
            "J7:L7",
            f"RED: {red_label}",
        ),
        (
            "M7:N7",
            "CORTE: "
            + datetime.now().strftime(
                "%d/%m/%Y"
            ),
        ),
    ]

    for cell_range, value in filter_blocks:
        ws.merge_cells(cell_range)
        cell = ws[
            cell_range.split(":")[0]
        ]
        cell.value = value
        cell.font = Font(
            name="Arial",
            size=9,
            bold=True,
            color=C_MUTED,
        )
        cell.fill = PatternFill(
            "solid",
            fgColor=C_BG,
        )
        cell.alignment = Alignment(
            horizontal="center",
            vertical="center",
        )

        for row in ws[cell_range]:
            for c in row:
                c.border = border

    # -----------------------------------------------------------------
    # KPI Cards
    # -----------------------------------------------------------------

    def _kpi_card(
        cell_range,
        title,
        value,
        subtitle,
        fill_color,
        value_color=C_TEXT,
    ):
        start_cell = cell_range.split(":")[0]

        start_col = ws[start_cell].column
        start_row = ws[start_cell].row

        end_cell = cell_range.split(":")[1]
        end_col = ws[end_cell].column
        end_row = ws[end_cell].row

        for row in ws.iter_rows(
            min_row=start_row,
            max_row=end_row,
            min_col=start_col,
            max_col=end_col,
        ):
            for cell in row:
                cell.fill = PatternFill(
                    "solid",
                    fgColor=fill_color,
                )
                cell.border = border

        # Título.
        title_range = (
            f"{ws.cell(start_row, start_col).coordinate}:"
            f"{ws.cell(start_row, end_col).coordinate}"
        )
        ws.merge_cells(title_range)
        c_title = ws.cell(
            start_row,
            start_col,
        )
        c_title.value = title
        c_title.font = Font(
            name="Arial",
            size=9,
            bold=True,
            color=C_MUTED,
        )
        c_title.alignment = Alignment(
            horizontal="center",
            vertical="center",
        )

        # Valor.
        value_range = (
            f"{ws.cell(start_row + 1, start_col).coordinate}:"
            f"{ws.cell(end_row - 1, end_col).coordinate}"
        )
        ws.merge_cells(value_range)
        c_value = ws.cell(
            start_row + 1,
            start_col,
        )
        c_value.value = value
        c_value.font = Font(
            name="Arial",
            size=24,
            bold=True,
            color=value_color,
        )
        c_value.alignment = Alignment(
            horizontal="center",
            vertical="center",
        )

        # Subtítulo.
        sub_range = (
            f"{ws.cell(end_row, start_col).coordinate}:"
            f"{ws.cell(end_row, end_col).coordinate}"
        )
        ws.merge_cells(sub_range)
        c_sub = ws.cell(
            end_row,
            start_col,
        )
        c_sub.value = subtitle
        c_sub.font = Font(
            name="Arial",
            size=8,
            color=C_MUTED,
        )
        c_sub.alignment = Alignment(
            horizontal="center",
            vertical="center",
            wrap_text=True,
        )

    _kpi_card(
        "A9:D12",
        "CENTROS OFICIALES",
        total,
        "Universo oficial bajo el filtro activo",
        "F7FBFE",
        C_BLUE,
    )

    _kpi_card(
        "E9:H12",
        "OFERTA PROPIA",
        own,
        "Fuente: GCPS",
        "F7FBFE",
        C_BLUE,
    )

    _kpi_card(
        "I9:L12",
        "OFERTA EXTRAINSTITUCIONAL",
        extra,
        "Fuente: GCOP",
        C_LIGHT_ORANGE,
        C_ORANGE,
    )

    _kpi_card(
        "M9:N12",
        "SIN NIVEL",
        sin_nivel,
        (
            "Sin pendientes"
            if sin_nivel == 0
            else "Requiere revisión"
        ),
        (
            C_LIGHT_GREEN
            if sin_nivel == 0
            else C_LIGHT_YELLOW
        ),
        (
            C_GREEN
            if sin_nivel == 0
            else C_YELLOW
        ),
    )

    # -----------------------------------------------------------------
    # Datos para gráficos (hoja oculta)
    # -----------------------------------------------------------------

    # Oferta.
    ws_data.append(
        ["CONDICION", "CENTROS"]
    )
    ws_data.append(
        ["Oferta propia", own]
    )
    ws_data.append(
        ["Oferta extrainstitucional", extra]
    )

    # Nivel.
    level_start = 6
    ws_data.cell(
        row=level_start,
        column=1,
        value="NIVEL",
    )
    ws_data.cell(
        row=level_start,
        column=2,
        value="CENTROS",
    )

    for idx, level in enumerate(
        CHAR_LEVEL_ORDER,
        start=level_start + 1,
    ):
        ws_data.cell(
            row=idx,
            column=1,
            value=(
                _format_level_label(level)
                if level != "SIN NIVEL"
                else "Sin nivel"
            ),
        )
        ws_data.cell(
            row=idx,
            column=2,
            value=level_counts[level],
        )

    # Red x nivel.
    red_level_start = 13

    red_level_headers = [
        "RED",
        "Nivel I",
        "Nivel II",
        "Nivel III",
        "Sin nivel",
        "TOTAL",
    ]

    for col_idx, header in enumerate(
        red_level_headers,
        start=1,
    ):
        ws_data.cell(
            row=red_level_start,
            column=col_idx,
            value=header,
        )

    red_level_items = list(
        summary.get(
            "red_level_counts",
            {},
        ).items()
    )

    red_level_items = sorted(
        red_level_items,
        key=lambda item: (
            -sum(
                int(v or 0)
                for v in item[1].values()
            ),
            item[0],
        ),
    )[:10]

    for row_idx, (
        network,
        values,
    ) in enumerate(
        red_level_items,
        start=red_level_start + 1,
    ):
        row_values = [
            network,
            int(
                values.get("NIVEL I") or 0
            ),
            int(
                values.get("NIVEL II") or 0
            ),
            int(
                values.get("NIVEL III") or 0
            ),
            int(
                values.get("SIN NIVEL") or 0
            ),
        ]

        row_values.append(
            sum(row_values[1:])
        )

        for col_idx, value in enumerate(
            row_values,
            start=1,
        ):
            ws_data.cell(
                row=row_idx,
                column=col_idx,
                value=value,
            )

    # Departamento.
    dep_start = 27

    ws_data.cell(
        row=dep_start,
        column=1,
        value="DEPARTAMENTO",
    )
    ws_data.cell(
        row=dep_start,
        column=2,
        value="CENTROS",
    )

    dep_items = list(
        summary.get(
            "department_counts",
            {},
        ).items()
    )[:10]

    for row_idx, (
        department,
        count,
    ) in enumerate(
        dep_items,
        start=dep_start + 1,
    ):
        ws_data.cell(
            row=row_idx,
            column=1,
            value=department,
        )
        ws_data.cell(
            row=row_idx,
            column=2,
            value=int(count or 0),
        )

    # Tipos, usado en la lectura complementaria.
    type_start = 40

    ws_data.cell(
        row=type_start,
        column=1,
        value="TIPO_CENTRO",
    )
    ws_data.cell(
        row=type_start,
        column=2,
        value="CENTROS",
    )

    type_items = list(
        summary.get(
            "type_counts",
            {},
        ).items()
    )[:10]

    for row_idx, (
        center_type,
        count,
    ) in enumerate(
        type_items,
        start=type_start + 1,
    ):
        ws_data.cell(
            row=row_idx,
            column=1,
            value=center_type,
        )
        ws_data.cell(
            row=row_idx,
            column=2,
            value=int(count or 0),
        )

    # -----------------------------------------------------------------
    # Sección 1 - Composición
    # -----------------------------------------------------------------

    ws.merge_cells("A14:N14")
    ws["A14"] = (
        "1. COMPOSICIÓN DE LA OFERTA Y NIVEL DE ATENCIÓN"
    )
    ws["A14"].font = Font(
        name="Arial",
        size=11,
        bold=True,
        color=C_WHITE,
    )
    ws["A14"].fill = PatternFill(
        "solid",
        fgColor=C_DARK,
    )
    ws["A14"].alignment = Alignment(
        vertical="center",
    )

    # Pie Oferta.
    pie = PieChart()

    offer_labels = Reference(
        ws_data,
        min_col=1,
        min_row=2,
        max_row=3,
    )

    offer_data = Reference(
        ws_data,
        min_col=2,
        min_row=1,
        max_row=3,
    )

    pie.add_data(
        offer_data,
        titles_from_data=True,
    )

    pie.set_categories(
        offer_labels
    )

    pie.title = "Composición de la oferta"
    pie.height = 7.1
    pie.width = 10.7
    pie.legend.position = "b"

    pie.dataLabels = DataLabelList()
    pie.dataLabels.showPercent = True
    pie.dataLabels.showLeaderLines = True

    ws.add_chart(
        pie,
        "A16",
    )

    # Column Nivel.
    level_chart = BarChart()
    level_chart.type = "col"
    level_chart.grouping = "clustered"
    level_chart.style = 10

    level_data = Reference(
        ws_data,
        min_col=2,
        min_row=level_start,
        max_row=level_start + 4,
    )

    level_labels = Reference(
        ws_data,
        min_col=1,
        min_row=level_start + 1,
        max_row=level_start + 4,
    )

    level_chart.add_data(
        level_data,
        titles_from_data=True,
    )

    level_chart.set_categories(
        level_labels
    )

    level_chart.title = (
        "Distribución por nivel de atención"
    )

    level_chart.y_axis.title = "Centros"
    level_chart.height = 7.1
    level_chart.width = 13.0
    level_chart.legend = None

    ws.add_chart(
        level_chart,
        "H16",
    )

    # -----------------------------------------------------------------
    # Sección 2 - Distribución estratégica
    # -----------------------------------------------------------------

    ws.merge_cells("A30:N30")
    ws["A30"] = (
        "2. DISTRIBUCIÓN DE LA OFERTA"
    )
    ws["A30"].font = Font(
        name="Arial",
        size=11,
        bold=True,
        color=C_WHITE,
    )
    ws["A30"].fill = PatternFill(
        "solid",
        fgColor=C_DARK,
    )

    # Red x Nivel apilado.
    red_chart = BarChart()
    red_chart.type = "bar"
    red_chart.grouping = "stacked"
    red_chart.overlap = 100
    red_chart.style = 11

    if red_level_items:
        red_data = Reference(
            ws_data,
            min_col=2,
            max_col=5,
            min_row=red_level_start,
            max_row=(
                red_level_start
                + len(red_level_items)
            ),
        )

        red_labels = Reference(
            ws_data,
            min_col=1,
            min_row=red_level_start + 1,
            max_row=(
                red_level_start
                + len(red_level_items)
            ),
        )

        red_chart.add_data(
            red_data,
            titles_from_data=True,
        )

        red_chart.set_categories(
            red_labels
        )

    red_chart.title = (
        "Principales redes por nivel"
    )

    red_chart.x_axis.title = "Centros"
    red_chart.height = 8.5
    red_chart.width = 14.3
    red_chart.legend.position = "b"

    ws.add_chart(
        red_chart,
        "A32",
    )

    # Departamentos.
    dep_chart = BarChart()
    dep_chart.type = "bar"
    dep_chart.grouping = "clustered"
    dep_chart.style = 10

    if dep_items:
        dep_data = Reference(
            ws_data,
            min_col=2,
            min_row=dep_start,
            max_row=(
                dep_start
                + len(dep_items)
            ),
        )

        dep_labels = Reference(
            ws_data,
            min_col=1,
            min_row=dep_start + 1,
            max_row=(
                dep_start
                + len(dep_items)
            ),
        )

        dep_chart.add_data(
            dep_data,
            titles_from_data=True,
        )

        dep_chart.set_categories(
            dep_labels
        )

    dep_chart.title = (
        "Distribución territorial"
    )

    dep_chart.x_axis.title = "Centros"
    dep_chart.height = 8.5
    dep_chart.width = 11.7
    dep_chart.legend = None

    ws.add_chart(
        dep_chart,
        "I32",
    )

    # -----------------------------------------------------------------
    # Sección 3 - Calidad y lectura gerencial
    # -----------------------------------------------------------------

    ws.merge_cells("A47:N47")
    ws["A47"] = (
        "3. CALIDAD DE CARACTERIZACIÓN Y LECTURA GERENCIAL"
    )
    ws["A47"].font = Font(
        name="Arial",
        size=11,
        bold=True,
        color=C_WHITE,
    )
    ws["A47"].fill = PatternFill(
        "solid",
        fgColor=C_DARK,
    )

    # Alertas.
    alert_specs = [
        (
            "A49:D52",
            "SIN NIVEL",
            sin_nivel,
        ),
        (
            "E49:H52",
            "SIN CATEGORÍA MINSA",
            sin_categoria,
        ),
        (
            "I49:L52",
            "SIN TIPO DE CENTRO",
            sin_tipo,
        ),
    ]

    for cell_range, title, value in alert_specs:
        fill_color = (
            C_LIGHT_GREEN
            if value == 0
            else C_LIGHT_YELLOW
        )

        value_color = (
            C_GREEN
            if value == 0
            else C_YELLOW
        )

        _kpi_card(
            cell_range,
            title,
            value,
            (
                "Sin pendientes"
                if value == 0
                else "Requiere revisión"
            ),
            fill_color,
            value_color,
        )

    # Indicador territorial destacado.
    _kpi_card(
        "M49:N52",
        "MAYOR CONCENTRACIÓN",
        int(top_department[1] or 0),
        str(top_department[0]),
        C_SOFT,
        C_BLUE,
    )

    # Narrativa.
    ws.merge_cells("A54:N58")
    ws["A54"] = (
        "LECTURA GERENCIAL\n"
        f"• {lectura_1}\n"
        f"• {lectura_2}\n"
        f"• {lectura_3}"
    )

    ws["A54"].font = Font(
        name="Arial",
        size=10,
        color=C_TEXT,
    )

    ws["A54"].fill = PatternFill(
        "solid",
        fgColor="F8FAFC",
    )

    ws["A54"].border = border

    ws["A54"].alignment = Alignment(
        horizontal="left",
        vertical="top",
        wrap_text=True,
    )

    # Pie institucional visible.
    ws.merge_cells("A60:N60")
    ws["A60"] = (
        f"Fuente: {fuente} · "
        "Maestro institucional SIEST · "
        "ES_VERSION_ACTUAL = 1 · ES_OFICIAL = 1"
    )
    ws["A60"].font = Font(
        name="Arial",
        size=8,
        italic=True,
        color=C_MUTED,
    )
    ws["A60"].border = Border(
        top=thin,
    )

    ws.merge_cells("A61:N61")
    ws["A61"] = (
        "Elaboración: Gerencia Central de Planeamiento y Presupuesto · "
        "Gerencia de Gestión de la Información · "
        "Sub Gerencia de Estadística"
    )
    ws["A61"].font = Font(
        name="Arial",
        size=8,
        color=C_MUTED,
    )

    ws.merge_cells("A62:N62")
    ws["A62"] = (
        "Documento generado automáticamente por SIEST · "
        "Uso institucional"
    )
    ws["A62"].font = Font(
        name="Arial",
        size=8,
        color="9AA5B4",
    )
    ws["A62"].alignment = Alignment(
        horizontal="center",
    )

    # -----------------------------------------------------------------
    # DETALLE_CENTROS
    # -----------------------------------------------------------------

    ws_detail.sheet_view.showGridLines = False

    detail_records = summary.get(
        "records",
        [],
    )

    detail_columns = [
        (
            "COD_EESS",
            "CÓD. EESS",
        ),
        (
            "COD_SES",
            "CÓD. SES",
        ),
        (
            "RENIPRESS",
            "RENIPRESS",
        ),
        (
            "NOMBRE_ESTABLECIMIENTO",
            "ESTABLECIMIENTO",
        ),
        (
            "RED_ASISTENCIAL",
            "RED",
        ),
        (
            "NIVEL",
            "NIVEL",
        ),
        (
            "CATEGORIA",
            "CATEGORÍA MINSA",
        ),
        (
            "TIPO_CENTRO",
            "TIPO DE CENTRO",
        ),
        (
            "CONDICION_CENTRO",
            "CONDICIÓN ESSALUD",
        ),
        (
            "ENTIDAD_VALIDADORA",
            "FUENTE / VALIDADOR",
        ),
        (
            "DEPARTAMENTO",
            "DEPARTAMENTO",
        ),
        (
            "PROVINCIA",
            "PROVINCIA",
        ),
        (
            "DISTRITO",
            "DISTRITO",
        ),
        (
            "UBIGEO",
            "UBIGEO",
        ),
    ]

    ws_detail.merge_cells("A1:N2")
    ws_detail["A1"] = (
        "DETALLE DE ESTABLECIMIENTOS · "
        f"{condicion_label} · FUENTE {fuente}"
    )
    ws_detail["A1"].font = Font(
        name="Arial",
        size=14,
        bold=True,
        color=C_WHITE,
    )
    ws_detail["A1"].fill = PatternFill(
        "solid",
        fgColor=C_BLUE,
    )
    ws_detail["A1"].alignment = Alignment(
        vertical="center",
    )

    for row in ws_detail["A1:N2"]:
        for cell in row:
            cell.fill = PatternFill(
                "solid",
                fgColor=C_BLUE,
            )

    headers = [
        label
        for _, label in detail_columns
    ]

    for col_idx, header in enumerate(
        headers,
        start=1,
    ):
        cell = ws_detail.cell(
            row=4,
            column=col_idx,
            value=header,
        )

        cell.font = Font(
            name="Arial",
            size=9,
            bold=True,
            color=C_WHITE,
        )

        cell.fill = PatternFill(
            "solid",
            fgColor=C_DARK,
        )

        cell.alignment = Alignment(
            horizontal="center",
            vertical="center",
            wrap_text=True,
        )

        cell.border = border

    for row_idx, record in enumerate(
        detail_records,
        start=5,
    ):
        for col_idx, (
            key,
            _label,
        ) in enumerate(
            detail_columns,
            start=1,
        ):
            value = record.get(key)

            cell = ws_detail.cell(
                row=row_idx,
                column=col_idx,
                value=value,
            )

            cell.font = Font(
                name="Arial",
                size=9,
                color=C_TEXT,
            )

            cell.alignment = Alignment(
                vertical="top",
                wrap_text=(
                    key
                    in {
                        "NOMBRE_ESTABLECIMIENTO",
                        "RED_ASISTENCIAL",
                    }
                ),
            )

            cell.border = border

            if row_idx % 2 == 0:
                cell.fill = PatternFill(
                    "solid",
                    fgColor="F8FAFC",
                )

    end_detail_row = max(
        5,
        4 + len(detail_records),
    )

    if detail_records:
        table = Table(
            displayName="DetalleCentrosSIEST",
            ref=(
                f"A4:N{end_detail_row}"
            ),
        )

        table_style = TableStyleInfo(
            name="TableStyleMedium2",
            showFirstColumn=False,
            showLastColumn=False,
            showRowStripes=True,
            showColumnStripes=False,
        )

        table.tableStyleInfo = table_style
        ws_detail.add_table(table)

    ws_detail.freeze_panes = "A5"
    ws_detail.auto_filter.ref = (
        f"A4:N{end_detail_row}"
    )

    detail_widths = {
        "A": 11,
        "B": 11,
        "C": 14,
        "D": 38,
        "E": 32,
        "F": 14,
        "G": 18,
        "H": 20,
        "I": 18,
        "J": 18,
        "K": 17,
        "L": 17,
        "M": 17,
        "N": 12,
    }

    for col, width in detail_widths.items():
        ws_detail.column_dimensions[
            col
        ].width = width

    # -----------------------------------------------------------------
    # Exportar en memoria
    # -----------------------------------------------------------------

    buffer = BytesIO()

    wb.save(buffer)
    buffer.seek(0)

    return buffer.getvalue(), total

