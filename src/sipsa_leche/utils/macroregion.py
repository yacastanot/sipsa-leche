"""Asignación de macrorregión lechera según COD_DEP.

SAS: IF COD_DEP in ('19','52','76','86') THEN MACRO='CAUCA,NARIÑO Y VALLE DEL CAUCA '
Fuente: MACRO LECHE.sas líneas 61-70 (%MACRO VALIDACION).
"""
from __future__ import annotations

import pandas as pd
import structlog

log = structlog.get_logger()


def assign_macroregion(df: pd.DataFrame, macroregiones: dict) -> pd.DataFrame:
    """Asigna columna MACRO según COD_DEP usando el dict de parameters.yml.

    El mapeo se invierte para vectorizar con pandas.map().
    Registra warning si hay COD_DEP sin macrorregión asignada.
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
