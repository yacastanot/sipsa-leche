"""Nodos del pipeline ingestion — M2: Lectura de la Encuesta de Leche Cruda en Finca.

SAS equivalente: %MACRO IMPORT → PROC IMPORT DATAFILE='BASE032026.xlsx' DBMS=XLSX GETNAMES=YES
MARZO_2026.sas líneas 22-27.
"""
from __future__ import annotations

import pandas as pd
import structlog

from sipsa_leche.validations.schemas_raw import BaseRawSchema

log = structlog.get_logger()


def snapshot_raw(base_raw_excel: pd.DataFrame) -> pd.DataFrame:
    """Valida el Excel de entrada y lo persiste como snapshot inmutable (bronze).

    El catálogo lee IDFINCA, VACASOR, PRECIOLITROS, PRODUCCION y VENTA como str
    para evitar que Excel convierta IDFINCs a float/notación científica.
    Falla de forma temprana (lazy=True) mostrando todas las violaciones de esquema.
    """
    BaseRawSchema.validate(base_raw_excel, lazy=True)
    log.info("snapshot_raw_ok", n_registros=len(base_raw_excel))
    return base_raw_excel
