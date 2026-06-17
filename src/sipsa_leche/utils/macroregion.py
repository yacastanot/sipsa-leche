"""Asignación de macrorregión lechera según el código de departamento.

Las cinco macrorregiones lecheras del SIPSA agrupan los 32 departamentos colombianos
según sus patrones de producción. La asignación se define en ``parameters.yml``
(``macroregiones``) y puede actualizarse sin tocar código.

Nota: ``'CAUCA,NARIÑO Y VALLE DEL CAUCA '`` lleva un espacio al final — este
espacio es deliberado y proviene de la fuente SAS. Modificarlo rompería la
compatibilidad con las salidas históricas.
"""
from __future__ import annotations

import pandas as pd
import structlog

log = structlog.get_logger()


def assign_macroregion(df: pd.DataFrame, macroregiones: dict) -> pd.DataFrame:
    """Asigna la columna ``MACRO`` a cada fila según ``COD_DEP``.

    Invierte el diccionario ``macroregiones`` (macro → [codigos]) para crear un
    mapeo eficiente ``cod_dep → macro`` y lo aplica con ``pandas.Series.map``.

    Args:
        df: DataFrame que contiene la columna ``COD_DEP`` (string de 2 dígitos,
            ej. ``'05'`` para Antioquia).
        macroregiones: Diccionario ``{nombre_macro: [cod_dep, ...]}`` proveniente
            de ``parameters.yml['macroregiones']``.

    Returns:
        Copia del DataFrame con la columna ``MACRO`` agregada. Filas con
        ``COD_DEP`` no mapeado reciben ``NaN`` y se registran con warning.

    Raises:
        KeyError: Si ``df`` no contiene la columna ``COD_DEP``.

    Example:
        >>> import pandas as pd
        >>> macros = {'ZONA CAFETERA': ['05', '17'], 'RESTO': ['68', '73']}
        >>> df = pd.DataFrame({'COD_DEP': ['05', '73', '99']})
        >>> assign_macroregion(df, macros)['MACRO'].tolist()
        ['ZONA CAFETERA', 'RESTO', nan]
    """
    cod_to_macro: dict[str, str] = {
        cod: macro
        for macro, codigos in macroregiones.items()
        for cod in codigos
    }

    df = df.copy()
    df["MACRO"] = df["COD_DEP"].map(cod_to_macro)

    sin_macro = df["MACRO"].isna()
    if sin_macro.any():
        log.warning(
            "cod_dep_sin_macroregion",
            cod_dep_unicos=df.loc[sin_macro, "COD_DEP"].unique().tolist(),
            n_registros=int(sin_macro.sum()),
        )

    return df
