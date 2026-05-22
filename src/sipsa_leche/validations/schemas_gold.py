"""Schemas pandera para la capa Gold del pipeline SIPSA Leche."""
from __future__ import annotations

import pandera as pa
from pandera.typing import Series

TENDENCIAS_VALIDAS = ["xxx", "xx", "x", "=", "↑", "↑↑", "↑↑↑", ""]


class VariacionFincaSchema(pa.DataFrameModel):
    """Schema de FINCA_{MES_ACT}_{MES_ANT}.parquet."""

    IDFINCA: Series[str] = pa.Field(str_matches=r"^\d{7}$")
    TENDENCIA_PRECIO: Series[str] = pa.Field(
        isin=TENDENCIAS_VALIDAS, nullable=True
    )

    class Config:
        strict = False


class CorrelacionSchema(pa.DataFrameModel):
    """Schema de CORMUNI_{MES}.parquet y CORDEP_{MES}.parquet."""

    DEPARTAMENTO: Series[str]

    class Config:
        strict = False
