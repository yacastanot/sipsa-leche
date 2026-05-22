"""Utilidades para formateo y corrección de IDFINCA.

SAS equivalente: put(IDFINCA*1, Z7.) + 14 IF IDFINCA1=... THEN IDFINCA1=...
Fuente: MARZO_2026.sas líneas 59-77.
"""
from __future__ import annotations

import re

import pandas as pd
import structlog

log = structlog.get_logger()


def format_idfinca(raw_val: str) -> str:
    """Convierte IDFINCA a string de 7 dígitos con ceros a la izquierda.

    SAS: IDFINCA1 = put(IDFINCA*1, Z7.)

    Casos especiales:
    - Notación científica '07.69E7': Excel convierte 7689510 a esta forma.
      Se detecta y devuelve sin transformar para que apply_idfinca_corrections
      lo corrija por municipio.
    - 8+ dígitos (ej. '76895010'): se deja sin truncar; la corrección
      lo mapea al valor correcto de 7 dígitos.
    - Nulo / vacío: se devuelve tal cual.
    """
    if pd.isna(raw_val) or str(raw_val).strip() == "":
        return raw_val  # type: ignore[return-value]

    cleaned = str(raw_val).strip()

    # Detectar notación científica generada por Excel (ej. '07.69E7', '1.5E6')
    if re.match(r"^[\d.]+[eE]\d+$", cleaned):
        log.warning("idfinca_notacion_cientifica", valor=cleaned)
        return cleaned  # Corregido en apply_idfinca_corrections

    try:
        return str(int(float(cleaned))).zfill(7)
    except (ValueError, OverflowError):
        log.warning("idfinca_no_convertible", valor=cleaned)
        return cleaned


def apply_idfinca_corrections(
    df: pd.DataFrame, corrections: list[dict]
) -> pd.DataFrame:
    """Aplica las 14 correcciones de IDFINCA definidas en parameters.yml.

    SAS: IF IDFINCA1 = 'xxxx' AND MUNICIPIO = 'yyy' THEN IDFINCA1 = 'zzzz'
    MARZO_2026.sas líneas 63-77.

    Requiere coincidencia de IDFINCA Y MUNICIPIO para evitar falsos positivos.
    """
    df = df.copy()
    for corr in corrections:
        mask = (df["IDFINCA"] == corr["wrong"]) & (
            df["MUNICIPIO"] == corr["municipio"]
        )
        if mask.any():
            log.info(
                "correccion_idfinca_aplicada",
                wrong=corr["wrong"],
                correct=corr["correct"],
                municipio=corr["municipio"],
                n_registros=int(mask.sum()),
            )
            df.loc[mask, "IDFINCA"] = corr["correct"]
    return df
