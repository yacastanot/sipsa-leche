"""Estadísticas ponderadas por producción.

SAS usa varianza ponderada, NO la varianza muestral estándar:
  VAR_Y_PRECIO = PONMUNI * (PRECIOLITROS - ME_PRECIO_MUNI)^2
  SD_PRECIO_MUNI = SQRT(SUM(VAR_Y_PRECIO))

Esto es diferente de pandas .std(ddof=1) que usa varianza muestral.
Ver: MACRO LECHE.sas líneas 255-257 (%MACRO CUADROS, sección MUNICIPIO).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def weighted_mean(values: pd.Series, weights: pd.Series) -> float:
    """Media ponderada: SUM(v * w) / SUM(w).

    SAS: Y_PRECIO = PRECIOLITROS * PONMUNI; ME_PRECIO_MUNI = SUM(Y_PRECIO)
    Nota: en SAS los pesos ya suman 1 (PONMUNI = PRODUCCION / T_PRODUCCION_MUNI),
    por lo que SUM(Y_PRECIO) = Σ(precio_i * peso_i) directamente.
    """
    w = weights.fillna(0)
    total_w = w.sum()
    if total_w == 0:
        return float("nan")
    return float((values * w).sum() / total_w)


def weighted_std(values: pd.Series, weights: pd.Series) -> float:
    """Desviación estándar ponderada por producción.

    SAS:
      VAR_Y_PRECIO = PONMUNI * (PRECIOLITROS - ME_PRECIO_MUNI)^2
      SD_PRECIO_MUNI = SQRT(SUM(VAR_Y_PRECIO))

    Esta es la raíz de la varianza ponderada, NO la std muestral.
    Se usa para MUNICIPIO, DEPARTAMENTO y MACRO.
    """
    w = weights.fillna(0)
    total_w = w.sum()
    if total_w == 0:
        return float("nan")
    mean_w = (values * w).sum() / total_w
    variance = (w * (values - mean_w) ** 2).sum()
    return float(np.sqrt(variance))


def weighted_var(values: pd.Series, weights: pd.Series) -> float:
    """Varianza ponderada por producción.

    SAS: VAR_FINCA = SUM(VARFINCA) donde VARFINCA = ((PRECIO-MED_FINCA)^2)*PONFINCA
    Se usa a nivel finca.
    """
    w = weights.fillna(0)
    total_w = w.sum()
    if total_w == 0:
        return float("nan")
    mean_w = (values * w).sum() / total_w
    return float((w * (values - mean_w) ** 2).sum())
