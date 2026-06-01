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


class ExcluidasSchema(pa.DataFrameModel):
    """Schema de SALEN{PERI}.parquet — una fila por finca excluida del cálculo.

    SAS: tabla SALEN{PERI} generada en %VALIDACION (MACRO LECHE.sas líneas 81-87).
    Las columnas dinámicas SALEN{MES} y observaciones{MES} no se validan aquí
    porque su nombre depende del período (strict=False las ignora).
    """

    IDFINCA: Series[str] = pa.Field(str_matches=r"^\d{7}$", nullable=False)
    DEPARTAMENTO: Series[str] = pa.Field(nullable=False)
    COD_MUNI: Series[str] = pa.Field(str_matches=r"^\d{5}$", nullable=False)
    MUNICIPIO: Series[str] = pa.Field(nullable=False)
    IDDEPMUNI: Series[str] = pa.Field(nullable=False)
    FINCA: Series[str] = pa.Field(nullable=False)

    class Config:
        strict = False


class CoberturaSchema(pa.DataFrameModel):
    """Schema de COB_{MES}.parquet — cobertura por municipio.

    SAS: tabla COB_{MES} = MERGE VALIDOS SALENN BY IDDEPMUNI.
    Las columnas V{MES} y NO{MES} son dinámicas (strict=False las ignora).
    """

    DEPARTAMENTO: Series[str] = pa.Field(nullable=False)
    COD_MUNI: Series[str] = pa.Field(str_matches=r"^\d{5}$", nullable=False)
    MUNICIPIO: Series[str] = pa.Field(nullable=False)
    IDDEPMUNI: Series[str] = pa.Field(nullable=False)

    class Config:
        strict = False
