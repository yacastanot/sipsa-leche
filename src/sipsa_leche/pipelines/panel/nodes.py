"""Nodos del pipeline panel - M9: panel trimestral de fincas lecheras.

Implementa la macro SAS ``%PANEL`` de ``MACRO LECHE.sas``:
  - PANEL1: MERGE FINCA.PANEL + FINCA_{ACTUAL} por IDFINCA.
  - PANEL: conservar fincas con produccion en mes anterior y actual.
  - INSUMOS1/2/3: calcular litros ajustados, pesos y precios ponderados.
  - TOTAL: suma de PRE_{ANT}, PRE_{ACT}, T_PROD2_{ANT}, T_PROD2_{ACT}.
"""
from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd
import structlog

log = structlog.get_logger()

_CURRENT_INPUT_PREFIXES = ("T_VACAS", "T_PROD", "MED_FINCA")


def merge_panel_with_current(
    panel: pd.DataFrame,
    finca_actual: pd.DataFrame,
    mes_actual: str,
    mes_anterior: str,
) -> pd.DataFrame:
    """Actualiza el panel con el mes actual y conserva el panel balanceado.

    SAS:
      DATA PANEL1; MERGE FINCA.PANEL INSUMO1; BY IDFINCA;
      CREATE TABLE PANEL AS SELECT * FROM PANEL1
      WHERE T_PROD_{ANTERIOR} NE . AND T_PROD_{ACTUAL} NE .;
    """
    actual = _normalizar_mes(mes_actual)
    anterior = _normalizar_mes(mes_anterior)
    prod_anterior = f"T_PROD_{anterior}"
    prod_actual = f"T_PROD_{actual}"

    _require_columns(panel, ["IDFINCA", prod_anterior], "panel")
    current_cols = ["IDFINCA", *(f"{prefix}_{actual}" for prefix in _CURRENT_INPUT_PREFIXES)]
    _require_columns(finca_actual, current_cols, "finca_actual")

    panel_base = panel.copy()
    insumo = finca_actual[current_cols].copy()

    _prepare_idfinca(panel_base, "panel")
    _prepare_idfinca(insumo, "finca_actual")
    _ensure_unique(panel_base, "panel")
    _ensure_unique(insumo, "finca_actual")

    # Re-ejecucion idempotente: si el panel ya trae columnas del mes actual,
    # el insumo mensual las reemplaza como en el MERGE SAS.
    panel_base = panel_base.drop(columns=current_cols[1:], errors="ignore")

    merged = (
        panel_base.sort_values("IDFINCA")
        .merge(insumo.sort_values("IDFINCA"), on="IDFINCA", how="outer")
        .sort_values("IDFINCA")
        .reset_index(drop=True)
    )
    balanceado = merged[merged[prod_anterior].notna() & merged[prod_actual].notna()].copy()

    log.info(
        "panel_balanceado_ok",
        mes_actual=actual,
        mes_anterior=anterior,
        fincas=len(balanceado),
    )
    return balanceado.reset_index(drop=True)


def compute_panel_weights(
    panel: pd.DataFrame,
    mes_actual: str,
    mes_anterior: str,
    n1: float = 0,
    d1: float = 1,
    n2: float = 0,
    d2: float = 1,
) -> pd.DataFrame:
    """Calcula litros ajustados y participacion de cada finca en el panel."""
    actual = _normalizar_mes(mes_actual)
    anterior = _normalizar_mes(mes_anterior)
    prod_anterior = f"T_PROD_{anterior}"
    prod_actual = f"T_PROD_{actual}"

    _require_columns(panel, ["IDFINCA", prod_anterior, prod_actual], "panel")
    _validate_denominator(d1, "D1")
    _validate_denominator(d2, "D2")

    df = panel.drop(
        columns=[
            f"T_PROD2_{anterior}",
            f"T_PROD2_{actual}",
            f"T_PROD1_{anterior}",
            f"T_PROD1_{actual}",
            f"P_{anterior}",
            f"P_{actual}",
        ],
        errors="ignore",
    ).copy()

    df[f"T_PROD2_{anterior}"] = df[prod_anterior] * (1 + float(n1) / float(d1))
    df[f"T_PROD2_{actual}"] = df[prod_actual] * (1 + float(n2) / float(d2))

    total_anterior = float(df[prod_anterior].sum(skipna=True))
    total_actual = float(df[prod_actual].sum(skipna=True))
    df[f"T_PROD1_{anterior}"] = total_anterior
    df[f"T_PROD1_{actual}"] = total_actual

    df[f"P_{anterior}"] = _safe_ratio(df[prod_anterior], total_anterior)
    df[f"P_{actual}"] = _safe_ratio(df[prod_actual], total_actual)

    log.info(
        "panel_weights_ok",
        mes_actual=actual,
        mes_anterior=anterior,
        total_anterior=total_anterior,
        total_actual=total_actual,
    )
    return df


def compute_panel_prices(
    panel: pd.DataFrame,
    mes_actual: str,
    mes_anterior: str,
) -> pd.DataFrame:
    """Calcula PRE_{ANTERIOR} y PRE_{ACTUAL} ponderados por produccion."""
    actual = _normalizar_mes(mes_actual)
    anterior = _normalizar_mes(mes_anterior)
    required = [
        f"P_{anterior}",
        f"P_{actual}",
        f"MED_FINCA_{anterior}",
        f"MED_FINCA_{actual}",
    ]
    _require_columns(panel, required, "panel")

    df = panel.drop(columns=[f"PRE_{anterior}", f"PRE_{actual}"], errors="ignore").copy()
    df[f"PRE_{anterior}"] = df[f"P_{anterior}"] * df[f"MED_FINCA_{anterior}"]
    df[f"PRE_{actual}"] = df[f"P_{actual}"] * df[f"MED_FINCA_{actual}"]

    log.info("panel_prices_ok", mes_actual=actual, mes_anterior=anterior)
    return df


def summarize_panel_total(
    panel: pd.DataFrame,
    mes_actual: str,
    mes_anterior: str,
) -> pd.DataFrame:
    """Genera la tabla TOTAL equivalente al PROC TABULATE de SAS."""
    actual = _normalizar_mes(mes_actual)
    anterior = _normalizar_mes(mes_anterior)
    cols = [
        f"PRE_{anterior}",
        f"PRE_{actual}",
        f"T_PROD2_{anterior}",
        f"T_PROD2_{actual}",
    ]
    _require_columns(panel, cols, "panel")

    total = {
        "MES_ANTERIOR": anterior,
        "MES_ACTUAL": actual,
        "N_FINCAS_PANEL": int(len(panel)),
    }
    total.update({col: float(panel[col].sum(skipna=True)) for col in cols})

    log.info("panel_total_ok", mes_actual=actual, mes_anterior=anterior, fincas=len(panel))
    return pd.DataFrame([total])


def construir_panel_trimestral(
    panel_persistido: pd.DataFrame,
    finca_actual: pd.DataFrame,
    mes_actual: str,
    mes_anterior: str,
    panel_ajuste: Mapping[str, float] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Construye el detalle del panel trimestral y su tabla TOTAL.

    Args:
        panel_persistido: FINCA.PANEL historico con columnas del mes anterior.
        finca_actual: FINCA_{MES} calculado en M4.
        mes_actual: sufijo del mes actual, por ejemplo ``MAR``.
        mes_anterior: sufijo del mes anterior, por ejemplo ``FEB``.
        panel_ajuste: parametros N1/D1 y N2/D2 para T_PROD2.

    Returns:
        ``(panel_detalle, panel_total)``.
    """
    n1, d1, n2, d2 = _extract_adjustment(panel_ajuste)

    panel_balanceado = merge_panel_with_current(
        panel=panel_persistido,
        finca_actual=finca_actual,
        mes_actual=mes_actual,
        mes_anterior=mes_anterior,
    )
    panel_con_pesos = compute_panel_weights(
        panel=panel_balanceado,
        mes_actual=mes_actual,
        mes_anterior=mes_anterior,
        n1=n1,
        d1=d1,
        n2=n2,
        d2=d2,
    )
    panel_detalle = compute_panel_prices(panel_con_pesos, mes_actual, mes_anterior)
    panel_total = summarize_panel_total(panel_detalle, mes_actual, mes_anterior)

    return panel_detalle, panel_total


def _normalizar_mes(mes: str) -> str:
    return str(mes).strip().upper()


def _require_columns(df: pd.DataFrame, columns: list[str], label: str) -> None:
    missing = [col for col in columns if col not in df.columns]
    if missing:
        raise KeyError(f"{label} no contiene columnas requeridas: {missing}")


def _prepare_idfinca(df: pd.DataFrame, label: str) -> None:
    if df["IDFINCA"].isna().any():
        raise ValueError(f"{label} contiene IDFINCA nulos")
    df["IDFINCA"] = df["IDFINCA"].astype(str)


def _ensure_unique(df: pd.DataFrame, label: str) -> None:
    duplicated = df.loc[df["IDFINCA"].duplicated(), "IDFINCA"].unique()
    if len(duplicated) > 0:
        sample = ", ".join(map(str, duplicated[:5]))
        raise ValueError(f"{label} contiene IDFINCA duplicados: {sample}")


def _validate_denominator(value: float, name: str) -> None:
    if float(value) == 0:
        raise ValueError(f"{name} no puede ser cero en el ajuste del panel")


def _safe_ratio(series: pd.Series, denominator: float) -> pd.Series:
    if denominator == 0:
        return pd.Series(np.nan, index=series.index, dtype="float64")
    return series / denominator


def _extract_adjustment(panel_ajuste: Mapping[str, float] | None) -> tuple[float, float, float, float]:
    params = panel_ajuste or {}
    return (
        float(_get_param(params, "N1", 0)),
        float(_get_param(params, "D1", 1)),
        float(_get_param(params, "N2", 0)),
        float(_get_param(params, "D2", 1)),
    )


def _get_param(params: Mapping[str, float], name: str, default: float) -> float:
    return params.get(name, params.get(name.lower(), default))
