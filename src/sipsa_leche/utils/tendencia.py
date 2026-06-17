"""Clasificación de tendencia del precio del litro de leche.

Los umbrales difieren por nivel geográfico:
  - Finca/Municipio → bajo_leve = ±5%
  - Depto/Macro     → bajo_leve = ±3%  (umbral más estricto)

Los umbrales llegan desde ``parameters.yml`` (``tendencia_umbral_finca_muni``
y ``tendencia_umbral_dep_macro``) y son configurables sin tocar código.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def classify_tendency(variacion: float, umbrales: dict) -> str:
    """Clasifica la variación de precio en una de siete categorías simbólicas.

    Reproduce la lógica de las macros SAS:
    ``IF VPRE < -0.12 THEN TENDENCIA_PRECIO='xxx'; ...``

    Args:
        variacion: Variación proporcional del precio (ej. ``-0.08`` = −8%).
            Un valor NaN o None retorna cadena vacía.
        umbrales: Diccionario con seis cortes (``bajo_extremo``, ``bajo_fuerte``,
            ``bajo_leve``, ``estable_sup``, ``alto_leve``, ``alto_fuerte``).
            Proviene de ``parameters.yml``.

    Returns:
        Una de las cadenas ``'xxx'``, ``'xx'``, ``'x'``, ``'='``,
        ``'↑'``, ``'↑↑'`` o ``'↑↑↑'``. Cadena vacía si ``variacion`` es NaN.

    Example:
        >>> umbrales = {'bajo_extremo': -0.12, 'bajo_fuerte': -0.07,
        ...             'bajo_leve': -0.05, 'estable_sup': 0.05,
        ...             'alto_leve': 0.07, 'alto_fuerte': 0.12}
        >>> classify_tendency(-0.15, umbrales)
        'xxx'
        >>> classify_tendency(0.02, umbrales)
        '='
        >>> classify_tendency(float('nan'), umbrales)
        ''
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
    """Aplica ``classify_tendency`` vectorialmente sobre una columna de variación.

    Args:
        df: DataFrame con al menos la columna ``variacion_col``.
        variacion_col: Nombre de la columna que contiene la variación proporcional.
        umbrales: Diccionario de umbrales (ver ``classify_tendency``).
        output_col: Nombre de la columna de salida. Por defecto ``'TENDENCIA_PRECIO'``.

    Returns:
        Copia del DataFrame con la columna ``output_col`` agregada.

    Example:
        >>> import pandas as pd
        >>> umbrales = {'bajo_extremo': -0.12, 'bajo_fuerte': -0.07,
        ...             'bajo_leve': -0.05, 'estable_sup': 0.05,
        ...             'alto_leve': 0.07, 'alto_fuerte': 0.12}
        >>> df = pd.DataFrame({'VPRE': [-0.15, 0.02, 0.10]})
        >>> apply_tendency_column(df, 'VPRE', umbrales)['TENDENCIA_PRECIO'].tolist()
        ['xxx', '=', '↑↑']
    """
    df = df.copy()
    df[output_col] = df[variacion_col].apply(
        lambda v: classify_tendency(v, umbrales)
    )
    return df
