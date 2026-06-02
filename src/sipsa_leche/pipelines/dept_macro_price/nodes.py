"""Nodos del pipeline dept_macro_price — M6: Precio por departamento y macrorregión.

Implementa las secciones DEPARTAMENTO y MACROREGION del macro %CUADROS
(MACRO LECHE.sas líneas 287-393):

  Departamento (Acts 37-39):
    DEPT1-6: PONDEP, ME_PRECIO_DEP, SD_PRECIO_DEP ponderadas por litros
    DEPARTAMENTO_{MES}: 13 variables sufijadas con mes + PON_NAL

  Macrorregión (Acts 40-41):
    PORMACRO 1-4: PONMACRO, ME_PRECIO_MACRO, SD_PRECIO_MACRO
    MACRO_{MES}: 10 variables — atención al naming SIN guión antes de &MES

Convención de nombres (del código SAS con &MES="MAR"):
  DEPARTAMENTO: MINPRECIO_DEP_MAR, ME_PRECIO_DEP_MAR, SDPRECIO_DEP_MAR, PON_NAL_MAR, …
  MACRO:        MINPRECIO_MACROMAR, ME_PRECIO_MACROMAR, SD_PRECIO_MACROMAR, PON_NACIONALMAR, …
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import structlog

log = structlog.get_logger()

_COLS_FIJAS_DEP = ["DEPARTAMENTO", "COD_DEP"]
_COLS_FIJAS_MAC = ["MACRO"]


def calcular_precio_departamento(
    df: pd.DataFrame,
    mes_actual: str,
) -> pd.DataFrame:
    """Precio medio ponderado y estadísticas por departamento.

    SAS: %CUADROS — sección DEPARTAMENTO, MACRO LECHE.sas líneas 287-342.
    Actos 37-39 del cronograma M6.
    """
    m = mes_actual

    # Filtrar base válida (mismo criterio M3/M4/M5)
    mask_valid = (
        (df["PRECIOLITROS"] > 0) & df["PRECIOLITROS"].notna()
        & (df["PRODUCCION"] > 0) & df["PRODUCCION"].notna()
    )
    base = df[mask_valid].copy()

    # TOTAL_NAL = SUM(PRODUCCION) nacional — scalar constante
    total_nal = base["PRODUCCION"].sum()

    # DEPARTAMENTO1: T_PRODUCCION_DEP, MIN/MAX precio por departamento
    dept1 = base.groupby("DEPARTAMENTO", sort=False).agg(
        T_PRODUCCION_DEP=("PRODUCCION", "sum"),
        MIN_PRECIO_DEP=("PRECIOLITROS", "min"),
        MAX_PRECIO_DEP=("PRECIOLITROS", "max"),
        COD_DEP=("COD_DEP", "max"),
    )
    # DEPARTAMENTO3: join T_PRODUCCION_DEP a cada fila
    base = base.join(dept1[["T_PRODUCCION_DEP", "MIN_PRECIO_DEP", "MAX_PRECIO_DEP"]], on="DEPARTAMENTO")

    # DEPARTAMENTO4: PONDEP = PRODUCCION/T_PRODUCCION_DEP; Y_PRECIO_DEP = PRECIOLITROS*PONDEP
    base["PONDEP"] = base["PRODUCCION"] / base["T_PRODUCCION_DEP"]
    base["Y_PRECIO_DEP"] = base["PRECIOLITROS"] * base["PONDEP"]

    # DEPARTAMENTO5: ME_PRECIO_DEP = SUM(Y_PRECIO_DEP) por departamento (media ponderada)
    me_precio_dep = (
        base.groupby("DEPARTAMENTO", sort=False)["Y_PRECIO_DEP"]
        .sum()
        .rename("ME_PRECIO_DEP")
    )
    base = base.join(me_precio_dep, on="DEPARTAMENTO")

    # DEPARTAMENTO6: VAR_Y_PRECIO_DEP; PON_NAL = T_PRODUCCION_DEP / TOTAL_NAL
    base["VAR_Y_PRECIO_DEP"] = base["PONDEP"] * (base["PRECIOLITROS"] - base["ME_PRECIO_DEP"]) ** 2
    # PON_NAL: participación del depto en la producción nacional
    # SAS: PONNAL = T_PRODUCCION_DEP / TOTAL_NAL (constante por depto)
    # La agregación SUM(PONNAL) GROUP BY DEPTO = T_PROD_DEP / TOTAL_NAL (1 finca-mes / registro)
    base["PONNAL"] = base["PRODUCCION"] / total_nal   # por fila → SUM = T_PROD_DEP/TOTAL_NAL

    # DEPARTAMENTO_{MES}: agregar todo por departamento
    result = (
        base.groupby("DEPARTAMENTO", sort=False)
        .agg(
            COD_DEP=("COD_DEP", "max"),
            _min_precio=("MIN_PRECIO_DEP", "min"),
            _max_precio=("MAX_PRECIO_DEP", "max"),
            _me_precio=("ME_PRECIO_DEP", "mean"),       # constante por depto
            _sd_precio=("VAR_Y_PRECIO_DEP", lambda x: np.sqrt(x.sum())),
            _tprod=("PRODUCCION", "sum"),
            _meprod=("PRODUCCION", "mean"),
            _sdprod=("PRODUCCION", lambda x: x.std(ddof=1)),
            _mevacas=("VACASOR", "mean"),
            _tvacas=("VACASOR", "sum"),
            _tventa=("VENTA", "sum"),
            _meventa=("VENTA", "mean"),
            _sdventa=("VENTA", lambda x: x.std(ddof=1)),
            _pon_nal=("PONNAL", "sum"),
        )
        .reset_index()
    )

    result = result.rename(columns={
        "_min_precio": f"MINPRECIO_DEP_{m}",
        "_max_precio": f"MAXPRECIO_DEP_{m}",
        "_me_precio":  f"ME_PRECIO_DEP_{m}",
        "_sd_precio":  f"SDPRECIO_DEP_{m}",
        "_tprod":      f"TPROD_DEP_{m}",
        "_meprod":     f"MEPROD_DEP_{m}",
        "_sdprod":     f"SDPROD_DEP_{m}",
        "_mevacas":    f"MEVACAS_DEP_{m}",
        "_tvacas":     f"TVACAS_DEP_{m}",
        "_tventa":     f"TVENTA_DEP_{m}",
        "_meventa":    f"MEVENTA_DEP_{m}",
        "_sdventa":    f"SDVENTA_DEP_{m}",
        "_pon_nal":    f"PON_NAL_{m}",
    })

    cols_din = [
        f"MINPRECIO_DEP_{m}", f"MAXPRECIO_DEP_{m}", f"ME_PRECIO_DEP_{m}",
        f"SDPRECIO_DEP_{m}", f"TPROD_DEP_{m}", f"MEPROD_DEP_{m}", f"SDPROD_DEP_{m}",
        f"MEVACAS_DEP_{m}", f"TVACAS_DEP_{m}", f"TVENTA_DEP_{m}",
        f"MEVENTA_DEP_{m}", f"SDVENTA_DEP_{m}", f"PON_NAL_{m}",
    ]
    result = result[_COLS_FIJAS_DEP + cols_din]

    log.info("dept_price_ok", mes=m, departamentos=len(result),
             pon_nal_total=round(float(result[f"PON_NAL_{m}"].sum()), 6))
    return result


def calcular_precio_macro(
    df: pd.DataFrame,
    mes_actual: str,
) -> pd.DataFrame:
    """Precio medio ponderado y estadísticas por macrorregión lechera.

    SAS: %CUADROS — sección MACROREGION, MACRO LECHE.sas líneas 344-393.
    Actos 40-41 del cronograma M6.

    Convención de nombres: las columnas NO llevan guión antes del sufijo de mes.
    SAS: `AS MINPRECIO_MACRO&MES` → con MES="MAR" → `MINPRECIO_MACROMAR`.
    """
    m = mes_actual

    # Filtrar base válida
    mask_valid = (
        (df["PRECIOLITROS"] > 0) & df["PRECIOLITROS"].notna()
        & (df["PRODUCCION"] > 0) & df["PRODUCCION"].notna()
    )
    base = df[mask_valid].copy()

    # TOTAL_NAL = SUM(PRODUCCION) nacional
    total_nal = base["PRODUCCION"].sum()

    # Excluir filas sin macrorregión asignada (COD_DEP fuera de las 5 macro zonas)
    base_macro = base[base["MACRO"].notna()].copy()
    # Normalizar: la clave 'CAUCA,NARIÑO Y VALLE DEL CAUCA ' lleva espacio en parameters.yml
    # pero la referencia SAS/Excel lo publica sin espacio final.
    base_macro["MACRO"] = base_macro["MACRO"].str.strip()

    # PORMACRO_1: T_PRODUCCION_MACRO, MIN/MAX precio por MACRO
    macro1 = base_macro.groupby("MACRO", sort=False).agg(
        T_PRODUCCION_MACRO=("PRODUCCION", "sum"),
        MIN_PRECIO_MACRO=("PRECIOLITROS", "min"),
        MAX_PRECIO_MACRO=("PRECIOLITROS", "max"),
    )
    # PORMACRO_2: join T_PRODUCCION_MACRO a cada fila; PONMACRO + Y_PRECIO_MACRO
    base_macro = base_macro.join(macro1[["T_PRODUCCION_MACRO", "MIN_PRECIO_MACRO", "MAX_PRECIO_MACRO"]], on="MACRO")
    base_macro["PONMACRO"] = base_macro["PRODUCCION"] / base_macro["T_PRODUCCION_MACRO"]
    base_macro["Y_PRECIO_MACRO"] = base_macro["PRECIOLITROS"] * base_macro["PONMACRO"]

    # PORMACRO_3: ME_PRECIO_MACRO = SUM(Y_PRECIO_MACRO) por MACRO
    me_precio_macro = (
        base_macro.groupby("MACRO", sort=False)["Y_PRECIO_MACRO"]
        .sum()
        .rename("ME_PRECIO_MACRO")
    )
    base_macro = base_macro.join(me_precio_macro, on="MACRO")

    # PORMACRO_4: VAR_Y_PRECIO_MACRO; PONNAL = PRODUCCION/TOTAL_NAL (per fila)
    base_macro["VAR_Y_PRECIO_MACRO"] = (
        base_macro["PONMACRO"] * (base_macro["PRECIOLITROS"] - base_macro["ME_PRECIO_MACRO"]) ** 2
    )
    base_macro["PONNAL"] = base_macro["PRODUCCION"] / total_nal

    # MACRO_{MES}: agregar todo por macrorregión
    # Naming SAS: `MINPRECIO_MACRO&MES` → sin guión bajo antes del sufijo mes
    result = (
        base_macro.groupby("MACRO", sort=False)
        .agg(
            _min_precio=("MIN_PRECIO_MACRO", "min"),
            _max_precio=("MAX_PRECIO_MACRO", "max"),
            _me_precio=("ME_PRECIO_MACRO", "mean"),      # constante por macro
            _sd_precio=("VAR_Y_PRECIO_MACRO", lambda x: np.sqrt(x.sum())),
            _t_vacas=("VACASOR", "sum"),
            _me_prod=("PRODUCCION", "mean"),
            _t_prod=("PRODUCCION", "sum"),
            _sd_prod=("PRODUCCION", lambda x: x.std(ddof=1)),
            _t_venta=("VENTA", "sum"),
            _pon_nal=("PONNAL", "sum"),
        )
        .reset_index()
    )

    # Renombrar con naming SAS (sin guión bajo entre MACRO y mes)
    result = result.rename(columns={
        "_min_precio": f"MINPRECIO_MACRO{m}",
        "_max_precio": f"MAXPRECIO_MACRO{m}",
        "_me_precio":  f"ME_PRECIO_MACRO{m}",
        "_sd_precio":  f"SD_PRECIO_MACRO{m}",
        "_t_vacas":    f"T_VACAS_MACRO{m}",
        "_me_prod":    f"ME_PRODUCCION_MACRO{m}",
        "_t_prod":     f"T_PRODUCCION_MACRO{m}",
        "_sd_prod":    f"SD_PRODUCCION_MACRO{m}",
        "_t_venta":    f"T_VENTA_MACRO{m}",
        "_pon_nal":    f"PON_NACIONAL{m}",
    })

    cols_din = [
        f"MINPRECIO_MACRO{m}", f"MAXPRECIO_MACRO{m}", f"ME_PRECIO_MACRO{m}",
        f"SD_PRECIO_MACRO{m}", f"T_VACAS_MACRO{m}", f"ME_PRODUCCION_MACRO{m}",
        f"T_PRODUCCION_MACRO{m}", f"SD_PRODUCCION_MACRO{m}", f"T_VENTA_MACRO{m}",
        f"PON_NACIONAL{m}",
    ]
    result = result[_COLS_FIJAS_MAC + cols_din]

    log.info("macro_price_ok", mes=m, macros=len(result),
             pon_nacional_total=round(float(result[f"PON_NACIONAL{m}"].sum()), 6))
    return result
