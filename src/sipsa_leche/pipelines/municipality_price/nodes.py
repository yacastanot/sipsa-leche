"""Nodos del pipeline municipality_price — M5: Precio medio del litro por municipio.

Implementa la sección MUNICIPIO del macro %CUADROS de MACRO LECHE.sas (líneas 219-284):
  Act 30 — MUNICIPIO2: T_PRODUCCION_MUNI, MIN/MAX precio por municipio
  Act 31 — MUNICIPIO3+4: PONMUNI, Y_PRECIO → ME_PRECIO_MUNI = SUM(Y_PRECIO)
  Act 32 — MUNICIPIO5: VAR_Y_PRECIO → SD_PRECIO_MUNI = SQRT(SUM(VAR_Y_PRECIO))
  Act 33 — PON_NAL = PRODUCCION/TOTAL_NAL → PON_NACIONAL_{MES} = SUM(PON_NAL) por municipio
  Act 34 — DEPARTAMENTOS: PRODDEP → PONDEPMUNI = T_PRODUCCION_MUNI / PRODDEP
  Act 35 — MUNICIPIO_{MES}: tabla final con todas las variables sufijadas
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import structlog

from sipsa_leche.validations.schemas_silver import MunicipioMesSchema

log = structlog.get_logger()

_COLS_FIJAS = ["DEPARTAMENTO", "MUNICIPIO", "COD_DEP", "COD_MUNI", "IDDEPMUNI"]


def calcular_precio_municipio(
    df: pd.DataFrame,
    mes_actual: str,
) -> pd.DataFrame:
    """Calcula el precio medio municipal ponderado y estadísticas asociadas.

    SAS: %CUADROS(&MES_A, &INI_MES) — sección MUNICIPIO, MACRO LECHE.sas líneas 219-284.

    Entrada:  base_peri_clean (incluye excluidas — se filtra internamente)
    Salida:   MUNICIPIO_{MES} — una fila por municipio con variables sufijadas
    """
    m = mes_actual

    # Filtrar base válida (igual que M3/M4)
    mask_valid = (
        (df["PRECIOLITROS"] > 0) & df["PRECIOLITROS"].notna()
        & (df["PRODUCCION"] > 0) & df["PRODUCCION"].notna()
    )
    base = df[mask_valid].copy()

    # IDDEPMUNI = COMPRESS(DEPARTAMENTO||MUNICIPIO) — elimina espacios
    base["IDDEPMUNI"] = (
        base["DEPARTAMENTO"] + base["MUNICIPIO"]
    ).str.replace(" ", "", regex=False)

    log.info("muni_price_base", municipios=int(base["IDDEPMUNI"].nunique()), filas=len(base))

    # Act 33 / MUNICIPIO1: TOTAL_NAL = SUM(PRODUCCION) nacional (constante en todo el df)
    total_nal = base["PRODUCCION"].sum()

    # Act 30 / MUNICIPIO2: T_PRODUCCION_MUNI, MIN_PRECIO_MUNI, MAX_PRECIO_MUNI por municipio
    muni2 = (
        base.groupby("IDDEPMUNI", sort=False)
        .agg(
            T_PRODUCCION_MUNI=("PRODUCCION", "sum"),
            MIN_PRECIO_MUNI=("PRECIOLITROS", "min"),
            MAX_PRECIO_MUNI=("PRECIOLITROS", "max"),
        )
    )
    base = base.join(muni2, on="IDDEPMUNI")

    # Act 31 / MUNICIPIO3: PONMUNI = PRODUCCION / T_PRODUCCION_MUNI
    #                       Y_PRECIO = PRECIOLITROS × PONMUNI
    base["PONMUNI"] = base["PRODUCCION"] / base["T_PRODUCCION_MUNI"]
    base["Y_PRECIO"] = base["PRECIOLITROS"] * base["PONMUNI"]

    # Act 31 / MUNICIPIO4: ME_PRECIO_MUNI = SUM(Y_PRECIO) por municipio
    # SAS: MEAN(ME_PRECIO_MUNI) en SALIDAMUNI = constante → equivalente a MAX/SUM
    me_precio = (
        base.groupby("IDDEPMUNI", sort=False)["Y_PRECIO"]
        .sum()
        .rename("ME_PRECIO_MUNI")
    )
    base = base.join(me_precio, on="IDDEPMUNI")

    # Act 32 / MUNICIPIO5: VAR_Y_PRECIO = PONMUNI × (precio − ME_PRECIO_MUNI)²
    base["VAR_Y_PRECIO"] = base["PONMUNI"] * (base["PRECIOLITROS"] - base["ME_PRECIO_MUNI"]) ** 2

    # Act 33 / MUNICIPIO5: PON_NAL = PRODUCCION / TOTAL_NAL
    base["PON_NAL"] = base["PRODUCCION"] / total_nal

    # Act 35 / SALIDAMUNI: agregar todo por municipio
    # SAS: SQRT(VAR(PRODUCCION)) usa ddof=1 (PROC SQL VAR())
    salidamuni = (
        base.groupby("IDDEPMUNI", sort=False)
        .agg(
            DEPARTAMENTO=("DEPARTAMENTO", "max"),
            MUNICIPIO=("MUNICIPIO", "max"),
            COD_DEP=("COD_DEP", "max"),
            COD_MUNI=("COD_MUNI", "max"),
            _min_precio=("MIN_PRECIO_MUNI", "min"),
            _max_precio=("MAX_PRECIO_MUNI", "max"),
            _me_precio=("ME_PRECIO_MUNI", "mean"),       # constante por municipio
            _sd_precio=("VAR_Y_PRECIO", lambda x: np.sqrt(x.sum())),
            _t_vacas=("VACASOR", "sum"),
            _me_prod=("PRODUCCION", "mean"),
            _t_prod=("PRODUCCION", "sum"),
            _sd_prod=("PRODUCCION", lambda x: x.std(ddof=1)),
            _t_venta=("VENTA", "sum"),
            _pon_nal=("PON_NAL", "sum"),
        )
        .reset_index()
    )

    # Renombrar columnas con sufijo mes
    salidamuni = salidamuni.rename(columns={
        "_min_precio": f"MINPRECIO_MUNI_{m}",
        "_max_precio": f"MAXPRECIO_MUNI_{m}",
        "_me_precio":  f"ME_PRECIO_MUNI_{m}",
        "_sd_precio":  f"SD_PRECIO_MUNI_{m}",
        "_t_vacas":    f"T_VACAS_MUNI_{m}",
        "_me_prod":    f"ME_PRODUCCION_MUNI_{m}",
        "_t_prod":     f"T_PRODUCCION_MUNI_{m}",
        "_sd_prod":    f"SD_PRODUCCION_MUNI_{m}",
        "_t_venta":    f"T_VENTA_MUNI_{m}",
        "_pon_nal":    f"PON_NACIONAL_{m}",
    })

    # Act 34 / DEPARTAMENTOS: PRODDEP_{MES} = SUM(PRODUCCION) por departamento
    proddep = (
        base.groupby("DEPARTAMENTO", sort=False)["PRODUCCION"]
        .sum()
        .rename(f"PRODDEP_{m}")
    )
    muni_mes = salidamuni.join(proddep, on="DEPARTAMENTO")

    # Act 34 / MUNICIPIO_{MES}: PONDEPMUNI = T_PRODUCCION_MUNI / PRODDEP
    muni_mes[f"PONDEPMUNI_{m}"] = (
        muni_mes[f"T_PRODUCCION_MUNI_{m}"] / muni_mes[f"PRODDEP_{m}"]
    )

    cols_din = [
        f"MINPRECIO_MUNI_{m}", f"MAXPRECIO_MUNI_{m}", f"ME_PRECIO_MUNI_{m}",
        f"SD_PRECIO_MUNI_{m}", f"T_VACAS_MUNI_{m}", f"ME_PRODUCCION_MUNI_{m}",
        f"T_PRODUCCION_MUNI_{m}", f"SD_PRODUCCION_MUNI_{m}", f"T_VENTA_MUNI_{m}",
        f"PON_NACIONAL_{m}", f"PRODDEP_{m}", f"PONDEPMUNI_{m}",
    ]
    muni_mes = muni_mes[_COLS_FIJAS + cols_din]

    MunicipioMesSchema.validate(muni_mes, lazy=True)
    log.info("muni_price_ok", mes=m, municipios=len(muni_mes),
             pon_nacional_total=round(float(muni_mes[f"PON_NACIONAL_{m}"].sum()), 6))
    return muni_mes
