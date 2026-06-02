"""Nodos del pipeline monthly_variation — M7: Variación mensual del precio y la producción.

Implementa la comparación intermensual equivalente a los DATA steps de MARZO_2026.sas
y al macro %COMPARACION de MACRO LECHE.sas (líneas 398-468):

  Act 44 — Variación cobertura: D1=(V_act/V_ant)-1, D2=V_act-V_ant
            CORRIGE bug SAS línea 116: usaba COB_MAR dos veces
  Act 45 — VPRE finca/muni/depto/macro = (ME_actual/ME_anterior) - 1
  Act 46 — VPROD finca/muni/depto/macro = (T_PROD_actual/T_PROD_anterior) - 1
  Act 47 — TENDENCIA_PRECIO finca/muni: 7 cat, umbral central ±5%
  Act 48 — TENDENCIA_PRECIO depto/macro: 7 cat, umbral central ±3%
  Act 49 — CV = SD_PRECIO / ME_PRECIO para municipio, departamento y macro

Convención de nombres (igual que la referencia CUADROS_032026_TOT.xls):
  FINCA:       VPRE_MARFEB, VPROD_FEBMAR        (act+ant, ant+act)
  MUNI/DEP/MACRO: VPRE_FEBMAR, VPROD_FEBMAR     (ant+act, ant+act)
  COBERTURA:   D1_MARFEB, D2_MARFEB            (act+ant)
"""
from __future__ import annotations

import pandas as pd
import structlog

from sipsa_leche.utils.tendencia import apply_tendency_column

log = structlog.get_logger()


# ─── Cobertura ────────────────────────────────────────────────────────────────

def calcular_variacion_cobertura(
    cob_actual: pd.DataFrame,
    cob_anterior: pd.DataFrame,
    mes_actual: str,
    mes_anterior: str,
) -> pd.DataFrame:
    """Variación de cobertura (fincas válidas) entre dos meses.

    SAS: DATA MUESTRAMAR_FEB: MERGE COB_MAR COB_FEB BY COD_MUNI — MARZO_2026.sas líneas 113-120
    CORRIGE BUG SAS: el original usaba COB_MAR dos veces; aquí se usa cob_anterior correctamente.

    D1 = (V_actual/V_anterior) - 1  (variación relativa)
    D2 = V_actual - V_anterior       (variación absoluta)
    """
    a, ant = mes_actual, mes_anterior
    v_act = f"V{a}"
    v_ant = f"V{ant}"

    merged = cob_actual.merge(cob_anterior[["COD_MUNI", v_ant]], on="COD_MUNI", how="outer")
    merged[f"D1_{a}{ant}"] = (merged[v_act] / merged[v_ant]) - 1
    merged[f"D2_{a}{ant}"] = merged[v_act] - merged[v_ant]

    log.info("variacion_cobertura_ok", mes=a, municipios=len(merged))
    return merged


# ─── Finca ────────────────────────────────────────────────────────────────────

def calcular_variacion_finca(
    finca_actual: pd.DataFrame,
    finca_anterior: pd.DataFrame,
    mes_actual: str,
    mes_anterior: str,
    tendencia_umbral_finca_muni: dict,
) -> pd.DataFrame:
    """Variación intermensual del precio y la producción por finca.

    SAS: DATA FINCA{MAR_FEB}: MERGE FINCA_FEB + FINCA_MAR BY IDFINCA — MARZO_2026.sas líneas 122-136.

    VPRE_MARFEB = (MED_FINCA_MAR / MED_FINCA_FEB) - 1   (naming: actual+anterior)
    VPROD_FEBMAR = (T_PROD_MAR / T_PROD_FEB) - 1         (naming: anterior+actual)
    TENDENCIA_PRECIO: 7 categorías con umbral central ±5%
    """
    a, ant = mes_actual, mes_anterior
    vpre_col = f"VPRE_{a}{ant}"
    vprod_col = f"VPROD_{ant}{a}"

    merged = finca_anterior.merge(finca_actual, on="IDFINCA", how="outer",
                                   suffixes=(f"_{ant}", f"_{a}"))

    # Usar las columnas del anterior que ya tienen sufijo (en caso de colisión)
    # Los DataFrames tienen columnas fijas sin sufijo + columnas dinámicas con sufijo
    med_a = f"MED_FINCA_{a}"
    med_ant = f"MED_FINCA_{ant}"
    prod_a = f"T_PROD_{a}"
    prod_ant = f"T_PROD_{ant}"

    merged[vpre_col] = (merged[med_a] / merged[med_ant]) - 1
    merged[vprod_col] = (merged[prod_a] / merged[prod_ant]) - 1
    merged = apply_tendency_column(merged, vpre_col, tendencia_umbral_finca_muni)

    log.info("variacion_finca_ok", mes=a, fincas=len(merged))
    return merged


# ─── Municipio ────────────────────────────────────────────────────────────────

def calcular_variacion_municipio(
    muni_actual: pd.DataFrame,
    muni_anterior: pd.DataFrame,
    mes_actual: str,
    mes_anterior: str,
    tendencia_umbral_finca_muni: dict,
) -> pd.DataFrame:
    """Variación intermensual del precio y la producción por municipio.

    SAS: DATA MUNI{FEB_MAR}: MERGE MUNICIPIO_FEB + MUNICIPIO_MAR BY IDDEPMUNI
         %COMPARACION macro — MACRO LECHE.sas líneas 416-425.

    VPRE_FEBMAR = (ME_PRECIO_MUNI_MAR / ME_PRECIO_MUNI_FEB) - 1
    VPROD_FEBMAR = (ME_PRODUCCION_MUNI_MAR / ME_PRODUCCION_MUNI_FEB) - 1
    CV = SD_PRECIO / ME_PRECIO   (para ambos meses — Act 49)
    """
    a, ant = mes_actual, mes_anterior
    vpre_col = f"VPRE_{ant}{a}"
    vprod_col = f"VPROD_{ant}{a}"

    merged = muni_anterior.merge(muni_actual, on="IDDEPMUNI", how="outer",
                                  suffixes=(f"_{ant}", f"_{a}"))

    # Resolver columnas fijas duplicadas (merge genera _MAR/_FEB variants)
    for col in ["DEPARTAMENTO", "MUNICIPIO", "COD_DEP", "COD_MUNI"]:
        if f"{col}_{a}" in merged.columns:
            merged[col] = merged[f"{col}_{a}"].fillna(merged.get(f"{col}_{ant}", pd.Series(dtype="object")))
            merged = merged.drop(columns=[f"{col}_{a}", f"{col}_{ant}"], errors="ignore")

    me_a = f"ME_PRECIO_MUNI_{a}"
    me_ant = f"ME_PRECIO_MUNI_{ant}"
    prod_a = f"ME_PRODUCCION_MUNI_{a}"
    prod_ant = f"ME_PRODUCCION_MUNI_{ant}"
    sd_a = f"SD_PRECIO_MUNI_{a}"
    sd_ant = f"SD_PRECIO_MUNI_{ant}"

    merged[vpre_col] = (merged[me_a] / merged[me_ant]) - 1
    merged[vprod_col] = (merged[prod_a] / merged[prod_ant]) - 1

    # Act 49: CV = SD / ME
    merged[f"CV_PRECIO_MUNI_{ant}"] = merged[sd_ant] / merged[me_ant]
    merged[f"CV_PRECIO_MUNI_{a}"] = merged[sd_a] / merged[me_a]

    merged = apply_tendency_column(merged, vpre_col, tendencia_umbral_finca_muni)

    log.info("variacion_municipio_ok", mes=a, municipios=len(merged))
    return merged


# ─── Departamento ─────────────────────────────────────────────────────────────

def calcular_variacion_departamento(
    dep_actual: pd.DataFrame,
    dep_anterior: pd.DataFrame,
    mes_actual: str,
    mes_anterior: str,
    tendencia_umbral_dep_macro: dict,
) -> pd.DataFrame:
    """Variación intermensual del precio y la producción por departamento.

    SAS: DATA DEP{FEB_MAR}: MERGE DEP_FEB + DEP_MAR BY DEPARTAMENTO
         %COMPARACION macro — MACRO LECHE.sas líneas 427-436.

    VPRE_FEBMAR = (ME_PRECIO_DEP_MAR / ME_PRECIO_DEP_FEB) - 1
    VPROD_FEBMAR = (TPROD_DEP_MAR / TPROD_DEP_FEB) - 1
    CV = SDPRECIO_DEP / ME_PRECIO_DEP   (Act 49)
    """
    a, ant = mes_actual, mes_anterior
    vpre_col = f"VPRE_{ant}{a}"
    vprod_col = f"VPROD_{ant}{a}"

    merged = dep_anterior.merge(dep_actual, on="DEPARTAMENTO", how="outer",
                                 suffixes=(f"_{ant}", f"_{a}"))

    for col in ["COD_DEP"]:
        if f"{col}_{a}" in merged.columns:
            merged[col] = merged[f"{col}_{a}"].fillna(merged.get(f"{col}_{ant}", pd.Series(dtype="object")))
            merged = merged.drop(columns=[f"{col}_{a}", f"{col}_{ant}"], errors="ignore")

    me_a = f"ME_PRECIO_DEP_{a}"
    me_ant = f"ME_PRECIO_DEP_{ant}"
    prod_a = f"TPROD_DEP_{a}"
    prod_ant = f"TPROD_DEP_{ant}"
    sd_a = f"SDPRECIO_DEP_{a}"
    sd_ant = f"SDPRECIO_DEP_{ant}"

    merged[vpre_col] = (merged[me_a] / merged[me_ant]) - 1
    merged[vprod_col] = (merged[prod_a] / merged[prod_ant]) - 1

    # Act 49: CV = SDPRECIO_DEP / ME_PRECIO_DEP
    merged[f"CV_PRECIO_DEP_{ant}"] = merged[sd_ant] / merged[me_ant]
    merged[f"CV_PRECIO_DEP_{a}"] = merged[sd_a] / merged[me_a]

    merged = apply_tendency_column(merged, vpre_col, tendencia_umbral_dep_macro)

    log.info("variacion_departamento_ok", mes=a, departamentos=len(merged))
    return merged


# ─── Macrorregión ─────────────────────────────────────────────────────────────

def calcular_variacion_macro(
    macro_actual: pd.DataFrame,
    macro_anterior: pd.DataFrame,
    mes_actual: str,
    mes_anterior: str,
    tendencia_umbral_dep_macro: dict,
) -> pd.DataFrame:
    """Variación intermensual del precio y la producción por macrorregión lechera.

    SAS: DATA MACRO{FEB_MAR}: MERGE MACRO_FEB + MACRO_MAR BY MACRO
         %COMPARACION macro — MACRO LECHE.sas líneas 438-447.

    VPRE_FEBMAR = (ME_PRECIO_MACROMAR / ME_PRECIO_MACROFEB) - 1
    VPROD_FEBMAR = (T_PRODUCCION_MACROMAR / T_PRODUCCION_MACROFEB) - 1
    CV = SD_PRECIO_MACRO / ME_PRECIO_MACRO   (Act 49)
    Naming: sin guión antes del sufijo (igual que M6).
    """
    a, ant = mes_actual, mes_anterior
    vpre_col = f"VPRE_{ant}{a}"
    vprod_col = f"VPROD_{ant}{a}"

    merged = macro_anterior.merge(macro_actual, on="MACRO", how="outer",
                                   suffixes=(ant, a))

    me_a = f"ME_PRECIO_MACRO{a}"
    me_ant = f"ME_PRECIO_MACRO{ant}"
    prod_a = f"T_PRODUCCION_MACRO{a}"
    prod_ant = f"T_PRODUCCION_MACRO{ant}"
    sd_a = f"SD_PRECIO_MACRO{a}"
    sd_ant = f"SD_PRECIO_MACRO{ant}"

    merged[vpre_col] = (merged[me_a] / merged[me_ant]) - 1
    merged[vprod_col] = (merged[prod_a] / merged[prod_ant]) - 1

    # Act 49: CV = SD_PRECIO_MACRO / ME_PRECIO_MACRO (sin guión antes del sufijo)
    merged[f"CV_PRECIO_MACRO{ant}"] = merged[sd_ant] / merged[me_ant]
    merged[f"CV_PRECIO_MACRO{a}"] = merged[sd_a] / merged[me_a]

    merged = apply_tendency_column(merged, vpre_col, tendencia_umbral_dep_macro)

    log.info("variacion_macro_ok", mes=a, macros=len(merged))
    return merged
