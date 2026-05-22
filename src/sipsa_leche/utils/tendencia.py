"""Clasificación de tendencia del precio del litro de leche.

SAS: IF VPRE_MARFEB < -0.12 THEN TENDENCIA_PRECIO='xxx'; ...
Fuente: MARZO_2026.sas líneas 129-191.

Los umbrales difieren por nivel geográfico:
  Finca/Municipio → bajo_leve = ±5%  (MARZO_2026.sas líneas 129-135, 145-152)
  Depto/Macro     → bajo_leve = ±3%  (MARZO_2026.sas líneas 164-170, 182-188)
Los umbrales llegan desde parameters.yml (tendencia_umbral_finca_muni / dep_macro).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def classify_tendency(variacion: float, umbrales: dict) -> str:
    """Clasifica la tendencia de precio en símbolos comparables con SAS.

    Retorna: 'xxx', 'xx', 'x', '=', '↑', '↑↑', '↑↑↑'
    Cadena vacía si la variación es NaN.
    """
    if pd.isna(variacion) or variacion is None:
        return ""

    u = umbrales
    if variacion < u["bajo_extremo"]:
        return "xxx"
    if variacion < u["bajo_fuerte"]:
        return "xx"
    if variacion < u["bajo_leve"]:
        return "x"
    if variacion < u["estable_sup"]:
        return "="
    if variacion < u["alto_leve"]:
        return "↑"
    if variacion < u["alto_fuerte"]:
        return "↑↑"
    return "↑↑↑"


def apply_tendency_column(
    df: pd.DataFrame,
    variacion_col: str,
    umbrales: dict,
    output_col: str = "TENDENCIA_PRECIO",
) -> pd.DataFrame:
    """Aplica classify_tendency vectorialmente sobre una columna de variación."""
    df = df.copy()
    df[output_col] = df[variacion_col].apply(
        lambda v: classify_tendency(v, umbrales)
    )
    return df
