"""Nodos del pipeline coverage — M3: Cobertura y fincas excluidas del cálculo.

Implementa el macro %VALIDACION de MACRO LECHE.sas (líneas 52-145):
  Act 15 — Clasificar cada finca en las 5 macrorregiones (ya hecho en M2)
  Act 16 — Identificar fincas con PRECIOLITROS=0 o PRODUCCION=0 (LECHENO)
  Act 17 — Construir SALEN{PERI}: una fila por finca excluida con detalle
  Act 18 — Exportar Excluidas_leche.xlsx (relé a catalog)
  Act 19 — Contar fincas válidas (V{MES}) y excluidas (NO{MES}) por municipio
  Act 20 — Construir COB_{MES}: merge VALIDOS + SALENN por IDDEPMUNI
"""
from __future__ import annotations

import pandas as pd
import structlog

from sipsa_leche.validations.schemas_silver import CoberturaSchema, ExcluidasSchema

log = structlog.get_logger()


def calcular_cobertura(
    df: pd.DataFrame,
    mes_actual: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Clasifica fincas en válidas y excluidas; construye SALEN y COB_{MES}.

    SAS: %VALIDACION(&BASE., &MES_A., SALEN&PERI., &INI_MES.) — MACRO LECHE.sas
    Parámetro mes_actual tomado de params:mes_actual (ej: "MAR").

    Returns:
        (salen, cob_mes)
    """
    # Act 16: Separar excluidas (precio=0 o producción=0 o nulos)
    # SAS: CREATE TABLE LECHENO AS ... WHERE PRECIOLITROS=0 OR PRECIOLITROS=. OR PRODUCCION=0 OR PRODUCCION=.
    mask_excluidas = (
        (df["PRECIOLITROS"] == 0.0) | df["PRECIOLITROS"].isna()
        | (df["PRODUCCION"] == 0.0) | df["PRODUCCION"].isna()
    )
    lecheno = df[mask_excluidas].copy()
    base_valida = df[~mask_excluidas].copy()

    log.info(
        "cobertura_clasificacion",
        total_filas=len(df),
        excluidas_filas=len(lecheno),
        validas_filas=len(base_valida),
        fincas_excluidas=int(lecheno["IDFINCA"].nunique()),
        fincas_validas=int(base_valida["IDFINCA"].nunique()),
    )

    # Act 17: SALEN{PERI} — una fila por finca excluida única (DEPT, MUNI, FINCA)
    # SAS: GROUP BY DEPARTAMENTO, MUNICIPIO, FINCA
    #      SELECT MAX(IDFINCA), MAX(COD_MUNI), COUNT(DISTINCT FINCA), MAX(OBSERVACIONES)
    salen_col = f"SALEN{mes_actual}"
    obs_col = f"observaciones{mes_actual}"

    salen = (
        lecheno
        .groupby(["DEPARTAMENTO", "MUNICIPIO", "FINCA"], sort=False, dropna=False)
        .agg(
            IDFINCA=("IDFINCA", "max"),
            COD_MUNI=("COD_MUNI", "max"),
            **{salen_col: ("FINCA", "nunique")},   # COUNT(DISTINCT FINCA) cuando GROUP BY FINCA = 1
            **{obs_col: ("observaciones", "max")},
        )
        .reset_index()
    )
    # COMPRESS(DEPARTAMENTO||MUNICIPIO) en SAS — eliminar todos los espacios
    salen["IDDEPMUNI"] = (
        salen["DEPARTAMENTO"] + salen["MUNICIPIO"]
    ).str.replace(" ", "", regex=False)
    salen = salen[[
        "IDFINCA", "DEPARTAMENTO", "COD_MUNI", "MUNICIPIO",
        "IDDEPMUNI", "FINCA", salen_col, obs_col,
    ]]

    ExcluidasSchema.validate(salen, lazy=True)

    # Acts 19-20: COB_{MES} — conteo por municipio
    cob = _build_cob(base_valida, salen, mes_actual)
    CoberturaSchema.validate(cob, lazy=True)

    return salen, cob


def exportar_excluidas_xlsx(salen: pd.DataFrame) -> pd.DataFrame:
    """Pasa el SALEN al catálogo Excel (act 18 — relé).

    SAS: %EXPORT → Excluidas_leche.xlsx
    El catálogo se encarga de persistir el DataFrame como Excel.
    """
    return salen


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _build_cob(
    base_valida: pd.DataFrame,
    salen: pd.DataFrame,
    mes_actual: str,
) -> pd.DataFrame:
    """Construye COB_{MES}: fincas válidas y excluidas por municipio.

    SAS:
      PROC TABULATE → VALIDOSS (N por DEPT/MUNI/COD_MUNI en base válida)
      PROC TABULATE → SALEN    (N por DEPT/MUNI/COD_MUNI en SALEN)
      DATA COB_{MES}: MERGE VALIDOS SALENN BY IDDEPMUNI
    """
    vmes = f"V{mes_actual}"
    nomes = f"NO{mes_actual}"

    # Fincas válidas distintas por municipio (PROC TABULATE sobre VALI)
    valid_farms = (
        base_valida
        .groupby(["DEPARTAMENTO", "MUNICIPIO", "FINCA"], sort=False)
        .agg(COD_MUNI=("COD_MUNI", "first"))
        .reset_index()
    )
    validos = (
        valid_farms
        .groupby(["DEPARTAMENTO", "COD_MUNI", "MUNICIPIO"])
        .size()
        .reset_index(name=vmes)
    )
    validos["IDDEPMUNI"] = (
        validos["DEPARTAMENTO"] + validos["MUNICIPIO"]
    ).str.replace(" ", "", regex=False)

    # Fincas excluidas distintas por municipio (PROC TABULATE sobre SAL)
    # salen ya tiene una fila por finca excluida única
    salenn = (
        salen
        .groupby(["DEPARTAMENTO", "COD_MUNI", "MUNICIPIO"])
        .size()
        .reset_index(name=nomes)
    )
    salenn["IDDEPMUNI"] = (
        salenn["DEPARTAMENTO"] + salenn["MUNICIPIO"]
    ).str.replace(" ", "", regex=False)

    # Merge por IDDEPMUNI — DATA COB_{MES}: MERGE VALIDOS SALENN BY IDDEPMUNI
    cob = validos.merge(
        salenn[["IDDEPMUNI", nomes]],
        on="IDDEPMUNI",
        how="left",
    )
    cob[nomes] = cob[nomes].fillna(0).astype(int)

    log.info(
        "cob_construida",
        mes=mes_actual,
        municipios=len(cob),
        total_validas=int(cob[vmes].sum()),
        total_excluidas=int(cob[nomes].sum()),
    )
    return cob
