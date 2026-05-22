"""Nodos del pipeline cleaning — M2: Depuración de la Encuesta de Leche Cruda en Finca.

Implementa el DATA step FINCA de MARZO_2026.sas (líneas 44-90):
  Act 6  — Cast numérico: VACASOR*1, PRECIOLITROS*1, PRODUCCION*1, VENTA*1
  Act 7  — Normalización: PROPCASE(MUNICIPIO/DEPARTAMENTO/FINCA), UPCASE(MES)
  Act 8  — Formato IDFINCA: put(IDFINCA*1, Z7.) → 7 dígitos con ceros
  Act 9  — Corrección JAMUNDÍ: 'JAMUNDI' → 'JAMUNDÍ'
  Act 10 — 14 correcciones de IDFINCA erróneas del formulario de campo
  Act 11 — Extracción COD_DEP (2 dígitos) y COD_MUNI (5 dígitos)
  Act 12 — Regla vacas: sin ordeño → precio/producción/venta = 0
  Act 13 — Regla venta: sin venta → precio no aplica (= 0)
"""
from __future__ import annotations

import pandas as pd
import structlog

from sipsa_leche.utils.idfinca import apply_idfinca_corrections, format_idfinca
from sipsa_leche.utils.macroregion import assign_macroregion
from sipsa_leche.validations.schemas_raw import BaseCleanSchema

log = structlog.get_logger()

_NUMERIC_COLS = ["VACASOR", "PRECIOLITROS", "PRODUCCION", "VENTA"]
_PROPCASE_COLS = ["FINCA", "MUNICIPIO", "DEPARTAMENTO"]


def depurar_base(
    df: pd.DataFrame,
    idfinca_corrections: list[dict],
    macroregiones: dict,
) -> pd.DataFrame:
    """Depura la base de finca aplicando todas las reglas del M2.

    Parámetros leídos desde parameters.yml:
      idfinca_corrections  — lista de 14 correcciones {wrong, municipio, correct}
      macroregiones        — dict macrorregión → lista de COD_DEP de 2 dígitos
    """
    df = df.copy()

    # Act 6: Convertir variables de texto a float64 — SAS: VACASOR*1, etc. (líneas 54-57)
    # Cast explícito a float64: pd.to_numeric devuelve int64 cuando no hay NaN,
    # pero BaseCleanSchema exige float64 (compatible con NaN en meses con datos faltantes).
    for col in _NUMERIC_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("float64")

    # Act 7: Normalizar nombres a título (PROPCASE) y MES a mayúsculas (UPCASE)
    # SAS: MUNICIPIO=PROPCASE(MUNICIPIO); MES=UPCASE(MES) — líneas 49-52
    for col in _PROPCASE_COLS:
        if col in df.columns:
            df[col] = df[col].str.strip().str.title()
    if "MES" in df.columns:
        df["MES"] = df["MES"].str.strip().str.upper()

    # Act 8: Formatear IDFINCA a exactamente 7 dígitos con ceros — SAS: put(IDFINCA*1,Z7.) línea 59
    df["IDFINCA"] = df["IDFINCA"].apply(format_idfinca)

    # Act 9: Corregir codificación del carácter especial Í — SAS: línea 61
    # Debe ejecutarse ANTES de apply_idfinca_corrections porque la corrección de
    # Jamundí (7636510→7636410) requiere MUNICIPIO='Jamundí' (con acento).
    mask_jamundi = df["MUNICIPIO"] == "Jamundi"
    if mask_jamundi.any():
        df.loc[mask_jamundi, "MUNICIPIO"] = "Jamundí"
        log.info("jamundi_corregido", n=int(mask_jamundi.sum()))

    # Act 10: Aplicar 14 correcciones de IDFINCA del formulario de campo — SAS: líneas 63-77
    df = apply_idfinca_corrections(df, idfinca_corrections)

    # Act 11: Extraer códigos geográficos del IDFINCA ya corregido — SAS: líneas 79-80
    df["COD_DEP"] = df["IDFINCA"].str[:2]
    df["COD_MUNI"] = df["IDFINCA"].str[:5]

    # Asignar macrorregión lechera según COD_DEP — MACRO LECHE.sas líneas 61-70
    df = assign_macroregion(df, macroregiones)

    # Act 12: Regla vacas — sin ordeño ese período, los tres indicadores son cero
    # SAS: IF VACASOR=. THEN VACASOR=0; IF VACASOR=0 THEN DO; ... END (líneas 82-83)
    df["VACASOR"] = df["VACASOR"].fillna(0.0)
    mask_sin_vacas = df["VACASOR"] == 0.0
    df.loc[mask_sin_vacas, ["PRECIOLITROS", "PRODUCCION", "VENTA"]] = 0.0

    # Act 13: Regla venta — sin venta, el precio reportado no aplica
    # SAS: IF VENTA=. THEN VENTA=0; IF VENTA=0 THEN PRECIOLITROS=0 (líneas 84-85)
    df["VENTA"] = df["VENTA"].fillna(0.0)
    mask_sin_venta = df["VENTA"] == 0.0
    df.loc[mask_sin_venta, "PRECIOLITROS"] = 0.0

    BaseCleanSchema.validate(df, lazy=True)
    log.info("base_depurada", n_registros=len(df))
    return df
