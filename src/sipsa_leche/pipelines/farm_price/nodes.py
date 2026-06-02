"""Nodos del pipeline farm_price — M4: Precio mensual del litro de leche por finca.

Implementa la sección FINCA del macro %CUADROS de MACRO LECHE.sas (líneas 152-217):
  Act 22 — FINCA1: PROD_TOTAL = SUM(PRODUCCION) por IDFINCA_AUX
  Act 23 — FINCA3: PONFINCA = PRODUCCION / PROD_TOTAL  (peso semanal)
  Act 24 — FINCA4+5: MEDFINCA = PRECIOLITROS × PONFINCA → MED_FINCA = SUM(MEDFINCA)
  Act 25 — FINCA6+7: VARFINCA = (precio - MED)² × PONFINCA → VAR_FINCA = SUM(VARFINCA)
  Act 26 — FINCA8: Agregar a una fila por finca (T_VACAS, T_PROD, T_VENTA, MIN/MAX precio)
  Act 27 — FINCA9+10: T_PROD_MUNI → PONMUNI = T_PROD / T_PROD_MUNI
  Act 28 — FINCA_{MES}: renombrar columnas con sufijo mes
"""
from __future__ import annotations

import pandas as pd
import structlog

from sipsa_leche.validations.schemas_silver import FincaMesSchema

log = structlog.get_logger()

# Columnas fijas en FINCA_{MES} (sin sufijo de mes)
_COLS_FIJAS = [
    "DEPARTAMENTO", "MUNICIPIO", "FINCA",
    "COD_DEP", "COD_MUNI", "IDFINCA", "IDFINCA_AUX",
]


def calcular_precio_finca(
    df: pd.DataFrame,
    mes_actual: str,
) -> pd.DataFrame:
    """Calcula el precio mensual ponderado por litros para cada finca válida.

    SAS: %CUADROS(&MES_A, &INI_MES) — sección FINCA, MACRO LECHE.sas líneas 152-217.

    Entrada:  base_peri_clean (9,276 filas, incluye excluidas)
    Salida:   FINCA_{MES} — una fila por finca válida con variables sufijadas
    """
    m = mes_actual

    # Filtrar base válida (igual que M3: excluir precio=0/null o producción=0/null)
    # SAS: DATA &base; SET TABLAA; IF (...) THEN DELETE; (dentro de %VALIDACION)
    mask_valid = (
        (df["PRECIOLITROS"] > 0) & df["PRECIOLITROS"].notna()
        & (df["PRODUCCION"] > 0) & df["PRODUCCION"].notna()
    )
    base = df[mask_valid].copy()
    log.info("farm_price_base_filtrada", fincas_validas=int(base["IDFINCA"].nunique()), filas=len(base))

    # Act 22 / FINCA2: IDFINCA_AUX = COMPRESS(DEPARTAMENTO || MUNICIPIO || FINCA)
    # SAS: COMPRESS(DEPARTAMENTO||MUNICIPIO||FINCA) — elimina todos los espacios
    base["IDFINCA_AUX"] = (
        base["DEPARTAMENTO"] + base["MUNICIPIO"] + base["FINCA"]
    ).str.replace(" ", "", regex=False)

    # Act 22 / FINCA1: PROD_TOTAL = SUM(PRODUCCION) por IDFINCA_AUX
    prod_total = (
        base.groupby("IDFINCA_AUX", sort=False)["PRODUCCION"]
        .sum()
        .rename("PROD_TOTAL")
    )
    base = base.join(prod_total, on="IDFINCA_AUX")

    # Act 23 / FINCA3: PONFINCA = PRODUCCION / PROD_TOTAL
    base["PONFINCA"] = base["PRODUCCION"] / base["PROD_TOTAL"]

    # Act 24 / FINCA4+5: MEDFINCA = PRECIOLITROS × PONFINCA → MED_FINCA = SUM(MEDFINCA) por finca
    base["MEDFINCA"] = base["PRECIOLITROS"] * base["PONFINCA"]
    med_finca = (
        base.groupby("IDFINCA_AUX", sort=False)["MEDFINCA"]
        .sum()
        .rename("MED_FINCA")
    )
    base = base.join(med_finca, on="IDFINCA_AUX")

    # Act 25 / FINCA6+7: VARFINCA = ((precio − MED_FINCA)² × PONFINCA) → VAR_FINCA = SUM
    base["VARFINCA"] = ((base["PRECIOLITROS"] - base["MED_FINCA"]) ** 2) * base["PONFINCA"]
    var_finca = (
        base.groupby("IDFINCA_AUX", sort=False)["VARFINCA"]
        .sum()
        .rename("VAR_FINCA")
    )
    base = base.join(var_finca, on="IDFINCA_AUX")

    # Act 26 / FINCA8: Una fila por finca — SUM vacas/prod/venta, MIN/MAX precio
    finca8 = (
        base.groupby("IDFINCA_AUX", sort=False)
        .agg(
            DEPARTAMENTO=("DEPARTAMENTO", "max"),
            MUNICIPIO=("MUNICIPIO", "max"),
            FINCA=("FINCA", "max"),
            COD_DEP=("COD_DEP", "max"),
            COD_MUNI=("COD_MUNI", "max"),
            IDFINCA=("IDFINCA", "max"),
            T_VACAS=("VACASOR", "sum"),
            T_PROD=("PRODUCCION", "sum"),
            T_VENTA=("VENTA", "sum"),
            MED_FINCA=("MED_FINCA", "max"),
            VAR_FINCA=("VAR_FINCA", "max"),
            MIN_PRECIO=("PRECIOLITROS", "min"),
            MAX_PRECIO=("PRECIOLITROS", "max"),
        )
        .reset_index()
    )

    # Act 27 / FINCA9+10: T_PROD_MUNI → PONMUNI = T_PROD / T_PROD_MUNI
    t_prod_muni = (
        finca8.groupby(["DEPARTAMENTO", "MUNICIPIO"], sort=False)["T_PROD"]
        .sum()
        .rename("T_PROD_MUNI")
    )
    finca10 = finca8.join(t_prod_muni, on=["DEPARTAMENTO", "MUNICIPIO"])
    finca10["PONMUNI"] = finca10["T_PROD"] / finca10["T_PROD_MUNI"]

    # Act 28 / FINCA_{MES}: Renombrar columnas con sufijo mes y seleccionar columnas finales
    finca_mes = finca10.rename(columns={
        "T_VACAS":    f"T_VACAS_{m}",
        "T_PROD":     f"T_PROD_{m}",
        "T_VENTA":    f"T_VENTA_{m}",
        "MIN_PRECIO": f"MIN_PRECIO_{m}",
        "MED_FINCA":  f"MED_FINCA_{m}",
        "MAX_PRECIO": f"MAX_PRECIO_{m}",
        "VAR_FINCA":  f"VAR_FINCA_{m}",
        "PONMUNI":    f"PONMUNI_{m}",
    })

    cols_dinamicas = [
        f"T_VACAS_{m}", f"T_PROD_{m}", f"T_VENTA_{m}",
        f"MIN_PRECIO_{m}", f"MED_FINCA_{m}", f"MAX_PRECIO_{m}",
        f"VAR_FINCA_{m}", f"PONMUNI_{m}",
    ]
    finca_mes = finca_mes[_COLS_FIJAS + cols_dinamicas]

    FincaMesSchema.validate(finca_mes, lazy=True)
    log.info("farm_price_ok", mes=m, n_fincas=len(finca_mes))
    return finca_mes
