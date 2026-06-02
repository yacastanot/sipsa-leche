"""Nodos del pipeline outputs — M10: Cuadros de salida para publicación.

Implementa el equivalente al %CONSULTA + %EXPORT de MARZO_2026.sas (líneas 194-246).
Produce 3 archivos Excel:
  1. CUADROS_{PERI}_TOT.xlsx — versión completa para análisis (4 hojas)
  2. CUADROS_{PERI}.xlsx    — versión resumida para publicación (4 hojas)
  3. COBERTURA.xlsx          — variación de cobertura (1 hoja COB)

Los selectores de columnas siguen exactamente el %CONSULTA SAS (MUNI_2/3, DEP_2/3, MACRO_2/3).
La FINCA usa todas las columnas disponibles del merge M7 + columnas fijas reconstruidas.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import structlog

log = structlog.get_logger()

# ─── Selectores de columnas (equivalente a %CONSULTA SAS) ─────────────────────

def _cols_finca_tot(ant: str, act: str) -> list[str]:
    """FINCA_2: 26 columnas — igual que CUADROS_TOT.xlsx FINCA sheet."""
    return [
        "DEPARTAMENTO", "MUNICIPIO", "FINCA", "COD_DEP", "COD_MUNI", "IDFINCA", "IDFINCA_AUX",
        f"T_VACAS_{ant}", f"T_PROD_{ant}", f"T_VENTA_{ant}",
        f"MIN_PRECIO_{ant}", f"MED_FINCA_{ant}", f"MAX_PRECIO_{ant}",
        f"VAR_FINCA_{ant}", f"PONMUNI_{ant}",
        f"T_VACAS_{act}", f"T_PROD_{act}", f"T_VENTA_{act}",
        f"MIN_PRECIO_{act}", f"MED_FINCA_{act}", f"MAX_PRECIO_{act}",
        f"VAR_FINCA_{act}", f"PONMUNI_{act}",
        f"VPRE_{act}{ant}", "TENDENCIA_PRECIO", f"VPROD_{ant}{act}",
    ]


def _cols_muni_tot(ant: str, act: str) -> list[str]:
    """MUNI_2: 34 columnas — versión completa TOT."""
    return [
        "DEPARTAMENTO", "MUNICIPIO", "COD_DEP", "COD_MUNI", "IDDEPMUNI",
        f"MINPRECIO_MUNI_{ant}", f"MAXPRECIO_MUNI_{ant}", f"ME_PRECIO_MUNI_{ant}",
        f"SD_PRECIO_MUNI_{ant}", f"CV_PRECIO_MUNI_{ant}", f"T_VACAS_MUNI_{ant}",
        f"ME_PRODUCCION_MUNI_{ant}", f"T_PRODUCCION_MUNI_{ant}", f"SD_PRODUCCION_MUNI_{ant}",
        f"T_VENTA_MUNI_{ant}", f"PON_NACIONAL_{ant}", f"PRODDEP_{ant}", f"PONDEPMUNI_{ant}",
        f"MINPRECIO_MUNI_{act}", f"MAXPRECIO_MUNI_{act}", f"ME_PRECIO_MUNI_{act}",
        f"SD_PRECIO_MUNI_{act}", f"CV_PRECIO_MUNI_{act}", f"T_VACAS_MUNI_{act}",
        f"ME_PRODUCCION_MUNI_{act}", f"T_PRODUCCION_MUNI_{act}", f"SD_PRODUCCION_MUNI_{act}",
        f"T_VENTA_MUNI_{act}", f"PON_NACIONAL_{act}", f"PRODDEP_{act}", f"PONDEPMUNI_{act}",
        f"VPRE_{ant}{act}", "TENDENCIA_PRECIO", f"VPROD_{ant}{act}",
    ]


def _cols_muni_pub(ant: str, act: str) -> list[str]:
    """MUNI_3: 20 columnas — versión resumida publicación."""
    return [
        "DEPARTAMENTO", "MUNICIPIO", "COD_DEP", "COD_MUNI", "IDDEPMUNI",
        f"MINPRECIO_MUNI_{ant}", f"MAXPRECIO_MUNI_{ant}", f"ME_PRECIO_MUNI_{ant}",
        f"CV_PRECIO_MUNI_{ant}", f"PON_NACIONAL_{ant}", f"PONDEPMUNI_{ant}",
        f"MINPRECIO_MUNI_{act}", f"MAXPRECIO_MUNI_{act}", f"ME_PRECIO_MUNI_{act}",
        f"CV_PRECIO_MUNI_{act}", f"PON_NACIONAL_{act}", f"PONDEPMUNI_{act}",
        f"VPRE_{ant}{act}", f"VPROD_{ant}{act}", "TENDENCIA_PRECIO",
    ]


def _cols_dep_tot(ant: str, act: str) -> list[str]:
    """DEP_2: 33 columnas — versión completa TOT."""
    return [
        "DEPARTAMENTO", "COD_DEP",
        f"MINPRECIO_DEP_{ant}", f"MAXPRECIO_DEP_{ant}", f"ME_PRECIO_DEP_{ant}",
        f"SDPRECIO_DEP_{ant}", f"CV_PRECIO_DEP_{ant}",
        f"TPROD_DEP_{ant}", f"MEPROD_DEP_{ant}", f"SDPROD_DEP_{ant}",
        f"MEVACAS_DEP_{ant}", f"TVACAS_DEP_{ant}",
        f"TVENTA_DEP_{ant}", f"MEVENTA_DEP_{ant}", f"SDVENTA_DEP_{ant}", f"PON_NAL_{ant}",
        f"MINPRECIO_DEP_{act}", f"MAXPRECIO_DEP_{act}", f"ME_PRECIO_DEP_{act}",
        f"SDPRECIO_DEP_{act}", f"CV_PRECIO_DEP_{act}",
        f"TPROD_DEP_{act}", f"MEPROD_DEP_{act}", f"SDPROD_DEP_{act}",
        f"MEVACAS_DEP_{act}", f"TVACAS_DEP_{act}",
        f"TVENTA_DEP_{act}", f"MEVENTA_DEP_{act}", f"SDVENTA_DEP_{act}", f"PON_NAL_{act}",
        f"VPRE_{ant}{act}", "TENDENCIA_PRECIO", f"VPROD_{ant}{act}",
    ]


def _cols_dep_pub(ant: str, act: str) -> list[str]:
    """DEP_3: 17 columnas — versión resumida publicación."""
    return [
        "DEPARTAMENTO", "COD_DEP",
        f"MINPRECIO_DEP_{ant}", f"MAXPRECIO_DEP_{ant}", f"ME_PRECIO_DEP_{ant}",
        f"SDPRECIO_DEP_{ant}", f"CV_PRECIO_DEP_{ant}", f"PON_NAL_{ant}",
        f"MINPRECIO_DEP_{act}", f"MAXPRECIO_DEP_{act}", f"ME_PRECIO_DEP_{act}",
        f"SDPRECIO_DEP_{act}", f"CV_PRECIO_DEP_{act}", f"PON_NAL_{act}",
        f"VPRE_{ant}{act}", f"VPROD_{ant}{act}", "TENDENCIA_PRECIO",
    ]


def _cols_macro_tot(ant: str, act: str) -> list[str]:
    """MACRO_2: 26 columnas — versión completa TOT (sin guión antes del mes)."""
    return [
        "MACRO",
        f"MINPRECIO_MACRO{ant}", f"MAXPRECIO_MACRO{ant}", f"ME_PRECIO_MACRO{ant}",
        f"SD_PRECIO_MACRO{ant}", f"CV_PRECIO_MACRO{ant}",
        f"T_VACAS_MACRO{ant}", f"ME_PRODUCCION_MACRO{ant}", f"T_PRODUCCION_MACRO{ant}",
        f"SD_PRODUCCION_MACRO{ant}", f"T_VENTA_MACRO{ant}", f"PON_NACIONAL{ant}",
        f"MINPRECIO_MACRO{act}", f"MAXPRECIO_MACRO{act}", f"ME_PRECIO_MACRO{act}",
        f"SD_PRECIO_MACRO{act}", f"CV_PRECIO_MACRO{act}",
        f"T_VACAS_MACRO{act}", f"ME_PRODUCCION_MACRO{act}", f"T_PRODUCCION_MACRO{act}",
        f"SD_PRODUCCION_MACRO{act}", f"T_VENTA_MACRO{act}", f"PON_NACIONAL{act}",
        f"VPRE_{ant}{act}", "TENDENCIA_PRECIO", f"VPROD_{ant}{act}",
    ]


def _cols_macro_pub(ant: str, act: str) -> list[str]:
    """MACRO_3: 15 columnas — versión resumida publicación."""
    return [
        "MACRO",
        f"MINPRECIO_MACRO{ant}", f"MAXPRECIO_MACRO{ant}", f"ME_PRECIO_MACRO{ant}",
        f"SD_PRECIO_MACRO{ant}", f"CV_PRECIO_MACRO{ant}", f"PON_NACIONAL{ant}",
        f"MINPRECIO_MACRO{act}", f"MAXPRECIO_MACRO{act}", f"ME_PRECIO_MACRO{act}",
        f"SD_PRECIO_MACRO{act}", f"CV_PRECIO_MACRO{act}", f"PON_NACIONAL{act}",
        f"VPRE_{ant}{act}", f"VPROD_{ant}{act}", "TENDENCIA_PRECIO",
    ]


def _cols_cob(act: str, ant: str) -> list[str]:
    """COBERTURA: columnas de variación de cobertura."""
    return [
        "DEPARTAMENTO", "COD_MUNI", "MUNICIPIO", "IDDEPMUNI",
        f"V{act}", f"NO{act}", f"V{ant}",
        f"D1_{act}{ant}", f"D2_{act}{ant}",
    ]


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _select(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Selecciona columnas presentes en el DataFrame (ignora las faltantes)."""
    available = [c for c in cols if c in df.columns]
    missing = [c for c in cols if c not in df.columns]
    if missing:
        log.warning("columnas_faltantes", count=len(missing), sample=missing[:3])
    return df[available].copy()


def _preparar_finca(var_finca: pd.DataFrame, ant: str, act: str) -> pd.DataFrame:
    """Reconstruye las columnas fijas duplicadas por el merge de M7."""
    df = var_finca.copy()
    for col in ["DEPARTAMENTO", "MUNICIPIO", "FINCA", "COD_DEP", "COD_MUNI"]:
        col_act = f"{col}_{act}"
        col_ant = f"{col}_{ant}"
        if col not in df.columns:
            if col_act in df.columns:
                df[col] = df[col_act].fillna(df.get(col_ant, pd.Series(dtype="object")))
            elif col_ant in df.columns:
                df[col] = df[col_ant]
    # IDFINCA_AUX
    if "IDFINCA_AUX" not in df.columns:
        aux_act = f"IDFINCA_AUX_{act}"
        aux_ant = f"IDFINCA_AUX_{ant}"
        if aux_act in df.columns:
            df["IDFINCA_AUX"] = df[aux_act].fillna(df.get(aux_ant, pd.Series(dtype="object")))
        elif aux_ant in df.columns:
            df["IDFINCA_AUX"] = df[aux_ant]
    return df


def _write_excel(path: Path, sheets: dict[str, pd.DataFrame]) -> None:
    """Escribe un Excel con múltiples hojas usando openpyxl."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(str(path), engine="openpyxl") as writer:
        for sheet_name, df in sheets.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    log.info("excel_escrito", path=str(path), hojas=list(sheets.keys()))


# ─── Nodo principal ───────────────────────────────────────────────────────────

def generar_cuadros_salida(
    variacion_finca: pd.DataFrame,
    variacion_municipio: pd.DataFrame,
    variacion_departamento: pd.DataFrame,
    variacion_macro: pd.DataFrame,
    variacion_cobertura: pd.DataFrame,
    mes_actual: str,
    mes_anterior: str,
    periodo: str,
) -> pd.DataFrame:
    """Genera los 3 archivos Excel de salida del proceso mensual.

    SAS: %CONSULTA + %EXPORT en MARZO_2026.sas líneas 194-246.
    Escribe CUADROS_{PERI}_TOT.xlsx, CUADROS_{PERI}.xlsx y COBERTURA.xlsx.

    Returns:
        DataFrame de 1 fila con registro de la ejecución (para trazabilidad Kedro).
    """
    m_act, m_ant = mes_actual, mes_anterior

    # ─── Preparar FINCA (reconstruir cols fijas del merge bilateral) ─────────
    finca_prep = _preparar_finca(variacion_finca, m_ant, m_act)

    # ─── CUADROS_TOT ────────────────────────────────────────────────────────
    finca_tot  = _select(finca_prep,          _cols_finca_tot(m_ant, m_act))
    muni_tot   = _select(variacion_municipio, _cols_muni_tot(m_ant, m_act))
    dep_tot    = _select(variacion_departamento, _cols_dep_tot(m_ant, m_act))
    macro_tot  = _select(variacion_macro,     _cols_macro_tot(m_ant, m_act))

    tot_path = Path(f"data/08_reporting/CUADROS_{periodo}_TOT.xlsx")
    _write_excel(tot_path, {
        "FINCA":        finca_tot,
        "MUNICIPIO":    muni_tot,
        "DEPARTAMENTO": dep_tot,
        "MACROREGION":  macro_tot,
    })

    # ─── CUADROS_PUB (resumen para publicación) ──────────────────────────────
    muni_pub  = _select(variacion_municipio,  _cols_muni_pub(m_ant, m_act))
    dep_pub   = _select(variacion_departamento, _cols_dep_pub(m_ant, m_act))
    macro_pub = _select(variacion_macro,      _cols_macro_pub(m_ant, m_act))

    pub_path = Path(f"data/08_reporting/CUADROS_{periodo}.xlsx")
    _write_excel(pub_path, {
        "FINCA":        finca_tot,        # misma hoja FINCA en ambos archivos
        "MUNICIPIO":    muni_pub,
        "DEPARTAMENTO": dep_pub,
        "MACROREGION":  macro_pub,
    })

    # ─── COBERTURA ───────────────────────────────────────────────────────────
    cob = _select(variacion_cobertura, _cols_cob(m_act, m_ant))
    _write_excel(Path("data/08_reporting/COBERTURA.xlsx"), {"COB": cob})

    log.info("cuadros_ok", periodo=periodo, mes=m_act,
             fincas=len(finca_tot), municipios=len(muni_tot),
             departamentos=len(dep_tot), macros=len(macro_tot))

    return pd.DataFrame([{
        "periodo": periodo, "mes_actual": m_act, "mes_anterior": m_ant,
        "fincas": len(finca_tot), "municipios": len(muni_tot),
        "departamentos": len(dep_tot), "macros": len(macro_tot),
        "archivos": 3,
    }])
