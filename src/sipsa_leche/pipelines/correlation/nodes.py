"""Nodos del pipeline correlation — M8: Correlación precio/producción y precio/venta.

Implementa el macro %COR de MACRO LECHE.sas (equivalente a PROC CORR de SAS):
  Act 51 — Correlación Pearson precio vs producción por municipio → PRECIOPROD_{MES}
  Act 52 — Correlación Pearson precio vs venta por municipio → PRECIOVENTA_{MES}
  Act 53 — Tabla CORMUNI_{MES}: DEPARTAMENTO, MUNICIPIO, IDDEPMUNIM, ambas correlaciones
  Act 54 — Tabla CORDEP_{MES}: DEPARTAMENTO, ambas correlaciones
            Nota: typo SAS conservado — columna se llama PROCIOPROD_{MES} (no PRECIOPROD)

Input: base_peri_clean (9,276 filas incluyendo excluidas — se filtra internamente)
La correlación se calcula sobre los registros SEMANALES (4 por finca por mes),
no sobre el promedio mensual, tal como lo hace PROC CORR en SAS.

pandas .corr() implementa Pearson con ddof=1 (igual que PROC CORR de SAS).
"""
from __future__ import annotations

import pandas as pd
import structlog

log = structlog.get_logger()


def calcular_correlaciones(
    df: pd.DataFrame,
    mes_actual: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Calcula correlaciones de Pearson precio/producción y precio/venta.

    SAS: %COR(&BASE, &INI_MES) — MACRO LECHE.sas.
    Filtra la base válida y calcula correlaciones por grupo geográfico.

    Returns:
        (cormuni, cordep)
    """
    m = mes_actual

    # Filtrar base válida (misma condición que M3/M4/M5)
    mask_valid = (
        (df["PRECIOLITROS"] > 0) & df["PRECIOLITROS"].notna()
        & (df["PRODUCCION"] > 0) & df["PRODUCCION"].notna()
    )
    base = df[mask_valid].copy()
    log.info("correlation_base", filas=len(base), municipios=int(base["MUNICIPIO"].nunique()))

    # ─── CORMUNI: correlación por (DEPARTAMENTO, MUNICIPIO) ───────────────────
    # SAS: PROC CORR BY DEPARTAMENTO MUNICIPIO; VAR PRODUCCION PRECIOLITROS; → _NAME_="PRODUCCION"
    #       PROC CORR BY DEPARTAMENTO MUNICIPIO; VAR VENTA PRECIOLITROS;     → _NAME_="VENTA"
    def _corr_muni(group: pd.DataFrame) -> pd.Series:
        return pd.Series({
            f"PRECIOPROD_{m}": group["PRECIOLITROS"].corr(group["PRODUCCION"]),
            f"PRECIOVENTA_{m}": group["PRECIOLITROS"].corr(group["VENTA"]),
        })

    cormuni = (
        base.groupby(["DEPARTAMENTO", "MUNICIPIO"], sort=False)
        .apply(_corr_muni)
        .reset_index()
    )
    # IDDEPMUNIM = COMPRESS(DEPARTAMENTO||MUNICIPIO) — elimina espacios
    cormuni["IDDEPMUNIM"] = (
        cormuni["DEPARTAMENTO"] + cormuni["MUNICIPIO"]
    ).str.replace(" ", "", regex=False)
    cormuni = cormuni[["DEPARTAMENTO", "MUNICIPIO", "IDDEPMUNIM",
                        f"PRECIOPROD_{m}", f"PRECIOVENTA_{m}"]]

    # ─── CORDEP: correlación por DEPARTAMENTO ────────────────────────────────
    # SAS: PROC CORR BY DEPARTAMENTO; VAR PRODUCCION PRECIOLITROS; → PROCIOPROD (typo SAS)
    #       PROC CORR BY DEPARTAMENTO; VAR VENTA PRECIOLITROS;     → PRECIOVENTA
    def _corr_dep(group: pd.DataFrame) -> pd.Series:
        return pd.Series({
            f"PRECIOVENTA_{m}": group["PRECIOLITROS"].corr(group["VENTA"]),
            f"PROCIOPROD_{m}": group["PRECIOLITROS"].corr(group["PRODUCCION"]),  # typo SAS conservado
        })

    cordep = (
        base.groupby("DEPARTAMENTO", sort=False)
        .apply(_corr_dep)
        .reset_index()
    )
    cordep = cordep[["DEPARTAMENTO", f"PRECIOVENTA_{m}", f"PROCIOPROD_{m}"]]

    log.info("correlation_ok", mes=m,
             municipios=len(cormuni), departamentos=len(cordep))
    return cormuni, cordep
