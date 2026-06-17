"""Nodos del pipeline preparation — M1: Preparación del archivo Excel de entrada.

Paso previo a la ingesta (M2):
  - Normaliza el nombre de la hoja de cálculo al mes correspondiente.
  - Persiste los encabezados de columnas como referencia para el próximo mes.
  - Valida la columna SEMANA: conteo de semanas de producción reportadas.
"""
from __future__ import annotations

from pathlib import Path

import openpyxl
import pandas as pd
import structlog

log = structlog.get_logger()

_DTYPE_RAW = {
    "IDFINCA": str,
    "VACASOR": str,
    "PRECIOLITROS": str,
    "PRODUCCION": str,
    "VENTA": str,
}


def preparar_hoja_excel(nombre_base: str, mes_nombre: str) -> pd.DataFrame:
    """Renombra la hoja del Excel de entrada al nombre del mes.

    Lee ``data/01_raw/{nombre_base}.xlsx``, renombra la primera hoja a
    ``mes_nombre`` (ej. "marzo") y guarda una copia en
    ``data/01_raw/{nombre_base}_ok.xlsx``.  Retorna el DataFrame listo para
    que el nodo ``snapshot_raw`` lo valide y persista como bronze.

    El archivo original no se modifica; la copia ``_ok`` es la que entra
    al pipeline.
    """
    ruta_entrada = Path("data/01_raw") / f"{nombre_base}.xlsx"
    ruta_salida = Path("data/01_raw") / f"{nombre_base}_ok.xlsx"

    wb = openpyxl.load_workbook(str(ruta_entrada))
    ws = wb.active
    hoja_original = ws.title

    # openpyxl compara títulos case-insensitivo al verificar unicidad.
    # Si el nombre actual difiere solo en mayúsculas (ej. "Marzo" → "marzo")
    # asignarlo directamente añadiría sufijo numérico ("marzo1").
    # Solución: pasar primero por un nombre temporal sin conflicto.
    if ws.title.lower() == mes_nombre.lower() and ws.title != mes_nombre:
        ws.title = "__tmp__"
    ws.title = mes_nombre

    wb.save(str(ruta_salida))
    wb.close()

    log.info(
        "hoja_renombrada",
        archivo_entrada=str(ruta_entrada),
        archivo_salida=str(ruta_salida),
        hoja_original=hoja_original,
        hoja_nueva=mes_nombre,
    )

    df = pd.read_excel(str(ruta_salida), sheet_name=mes_nombre, dtype=_DTYPE_RAW)
    log.info("excel_preparado_ok", n_registros=len(df), columnas=len(df.columns))
    return df


def guardar_cabeceras(df: pd.DataFrame) -> pd.DataFrame:
    """Persiste los encabezados de columnas del mes actual como referencia.

    El archivo resultante (``cabeceras_referencia`` en el catálogo) contiene
    una columna ``"columna"`` con los nombres en el mismo orden en que
    aparecen en la hoja del mes.  Sirve como plantilla para verificar que el
    próximo archivo mensual tenga la misma estructura de columnas.
    """
    cabeceras = pd.DataFrame({"columna": df.columns.tolist()})
    log.info("cabeceras_guardadas", columnas=df.columns.tolist())
    return cabeceras


def validar_semanas(df: pd.DataFrame, periodo: str, mes_nombre: str) -> pd.DataFrame:
    """Valida la columna SEMANA y retorna el resumen de semanas de producción.

    Cuenta cuántas semanas distintas de producción de leche se están reportando
    en el archivo del mes.  Un mes completo normalmente tiene 4 semanas; si hay
    menos emite una advertencia (datos incompletos o período parcial).

    El resultado (``semanas_validacion`` en el catálogo) contiene una fila por
    semana con: periodo, mes, semana, fincas (distintas) y registros (filas).
    """
    # La columna puede tener espacio al final dependiendo del Excel fuente
    col = "SEMANA " if "SEMANA " in df.columns else "SEMANA"

    conteo = (
        df.groupby(col, sort=True)
        .agg(
            fincas=("IDFINCA", "nunique"),
            registros=("IDFINCA", "count"),
        )
        .reset_index()
        .rename(columns={col: "semana"})
    )
    conteo.insert(0, "periodo", periodo)
    conteo.insert(1, "mes", mes_nombre)

    n_semanas = len(conteo)
    semanas_lista = conteo["semana"].tolist()

    if n_semanas < 4:
        log.warning(
            "semanas_incompletas",
            n_semanas=n_semanas,
            esperadas=4,
            periodo=periodo,
            semanas=semanas_lista,
        )
    else:
        log.info(
            "semanas_validadas",
            n_semanas=n_semanas,
            periodo=periodo,
            semanas=semanas_lista,
        )

    return conteo
