"""Schemas pandera para la capa Raw/Bronze del pipeline SIPSA Leche.

Valida la base de entrada después de depuración (BASE_{PERI}_clean.parquet).
Falla de forma temprana con mensaje descriptivo si hay violaciones de esquema.
"""
from __future__ import annotations

import pandera as pa
from pandera.typing import Series

MACROREGIONES_VALIDAS = [
    "CAUCA,NARIÑO Y VALLE DEL CAUCA ",
    "ZONA CAFETERA",
    "BOYACA Y CUNDINAMARCA",
    "COSTA ATLANTICA",
    "RESTO",
]


class BaseRawSchema(pa.DataFrameModel):
    """Schema del Excel de entrada antes de cualquier transformación."""

    IDFINCA: Series[str] = pa.Field(nullable=False)
    MUNICIPIO: Series[str] = pa.Field(nullable=False)
    DEPARTAMENTO: Series[str] = pa.Field(nullable=False)
    FINCA: Series[str] = pa.Field(nullable=False)
    VACASOR: Series[str] = pa.Field(nullable=True)
    PRECIOLITROS: Series[str] = pa.Field(nullable=True)
    PRODUCCION: Series[str] = pa.Field(nullable=True)
    VENTA: Series[str] = pa.Field(nullable=True)

    class Config:
        strict = False
        coerce = False


class BaseCleanSchema(pa.DataFrameModel):
    """Schema de la base después de depuración y reglas de negocio."""

    IDFINCA: Series[str] = pa.Field(
        str_matches=r"^\d{7}$",
        nullable=False,
        description="7 dígitos con ceros a la izquierda (put(IDFINCA*1,Z7.) en SAS)",
    )
    MUNICIPIO: Series[str] = pa.Field(nullable=False)
    DEPARTAMENTO: Series[str] = pa.Field(nullable=False)
    FINCA: Series[str] = pa.Field(nullable=False)
    COD_DEP: Series[str] = pa.Field(
        str_matches=r"^\d{2}$",
        description="2 dígitos extraídos de IDFINCA[:2]",
    )
    COD_MUNI: Series[str] = pa.Field(
        str_matches=r"^\d{5}$",
        description="5 dígitos extraídos de IDFINCA[:5]",
    )
    VACASOR: Series[float] = pa.Field(ge=0, nullable=True)
    PRECIOLITROS: Series[float] = pa.Field(ge=0, nullable=True)
    PRODUCCION: Series[float] = pa.Field(ge=0, nullable=True)
    VENTA: Series[float] = pa.Field(ge=0, nullable=True)
    MACRO: Series[str] = pa.Field(
        isin=MACROREGIONES_VALIDAS,
        nullable=True,
        description="Macrorregión lechera según COD_DEP",
    )

    class Config:
        strict = False
        coerce = False
