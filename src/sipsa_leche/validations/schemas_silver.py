"""Schemas pandera para la capa Silver del pipeline SIPSA Leche."""
from __future__ import annotations

import pandera as pa
from pandera.typing import Series


class FincaMesSchema(pa.DataFrameModel):
    """Schema de FINCA_{MES}.parquet — una fila por IDFINCA."""

    IDFINCA: Series[str] = pa.Field(str_matches=r"^\d{7}$")
    IDFINCA_AUX: Series[str] = pa.Field(nullable=False)
    DEPARTAMENTO: Series[str]
    MUNICIPIO: Series[str]
    FINCA: Series[str]
    COD_DEP: Series[str] = pa.Field(str_matches=r"^\d{2}$")
    COD_MUNI: Series[str] = pa.Field(str_matches=r"^\d{5}$")
    MACRO: Series[str] = pa.Field(nullable=True)

    class Config:
        strict = False


class MunicipioMesSchema(pa.DataFrameModel):
    """Schema de MUNICIPIO_{MES}.parquet — una fila por municipio."""

    DEPARTAMENTO: Series[str]
    MUNICIPIO: Series[str]
    COD_DEP: Series[str] = pa.Field(str_matches=r"^\d{2}$")
    COD_MUNI: Series[str] = pa.Field(str_matches=r"^\d{5}$")
    IDDEPMUNI: Series[str] = pa.Field(nullable=False)

    class Config:
        strict = False


class CoberturaSchema(pa.DataFrameModel):
    """Schema de COB_{MES}.parquet — cobertura por municipio."""

    DEPARTAMENTO: Series[str]
    MUNICIPIO: Series[str]
    IDDEPMUNI: Series[str] = pa.Field(nullable=False)
    COD_MUNI: Series[str] = pa.Field(str_matches=r"^\d{5}$")

    class Config:
        strict = False
