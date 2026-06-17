"""Estadísticas ponderadas por producción.

La varianza usada es **ponderada** (no muestral). ``pandas.std(ddof=1)`` produce
resultados distintos y NO es equivalente a estas funciones.

Equivalencia SAS (MACRO LECHE.sas, sección ``%MACRO CUADROS``)::

    Y_PRECIO     = PRECIOLITROS * PONMUNI;
    ME_PRECIO    = SUM(Y_PRECIO);           /* media ponderada */
    VAR_Y_PRECIO = PONMUNI * (PRECIOLITROS - ME_PRECIO)**2;
    SD_PRECIO    = SQRT(SUM(VAR_Y_PRECIO)); /* std ponderada   */
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def weighted_mean(values: pd.Series, weights: pd.Series) -> float:
    """Calcula la media ponderada Σ(v × w) / Σ(w).

    Args:
        values: Serie numérica con los valores (ej. precios por litro).
        weights: Serie de pesos no negativos (ej. ponderación de producción).
            Los NaN se tratan como cero.

    Returns:
        Media ponderada como ``float``. Retorna ``nan`` si la suma de pesos es cero.

    Example:
        >>> import pandas as pd
        >>> weighted_mean(pd.Series([2000, 2500, 1800]), pd.Series([0.5, 0.3, 0.2]))
        2190.0
    """
    w = weights.fillna(0)
    total_w = w.sum()
    if total_w == 0:
        return float("nan")
    return float((values * w).sum() / total_w)


def weighted_std(values: pd.Series, weights: pd.Series) -> float:
    """Calcula la desviación estándar ponderada √Σ(w × (v − μ)²).

    Esta es la raíz de la varianza ponderada, **no** la desviación estándar
    muestral. Se usa para los niveles municipio, departamento y macrorregión.

    Args:
        values: Serie numérica con los valores.
        weights: Serie de pesos no negativos. Los NaN se tratan como cero.

    Returns:
        Desviación estándar ponderada como ``float``.
        Retorna ``nan`` si la suma de pesos es cero.

    Example:
        >>> import pandas as pd
        >>> weighted_std(pd.Series([2000.0, 2500.0, 1800.0]), pd.Series([0.5, 0.3, 0.2]))
        263.8...
    """
    w = weights.fillna(0)
    total_w = w.sum()
    if total_w == 0:
        return float("nan")
    mean_w = (values * w).sum() / total_w
    variance = (w * (values - mean_w) ** 2).sum()
    return float(np.sqrt(variance))


def weighted_var(values: pd.Series, weights: pd.Series) -> float:
    """Calcula la varianza ponderada Σ(w × (v − μ)²).

    Se usa a nivel finca. Equivale a ``VAR_FINCA = SUM(VARFINCA)`` del SAS,
    donde ``VARFINCA = ((PRECIO - MED_FINCA)²) × PONFINCA``.

    Args:
        values: Serie numérica con los valores.
        weights: Serie de pesos no negativos. Los NaN se tratan como cero.

    Returns:
        Varianza ponderada como ``float``.
        Retorna ``nan`` si la suma de pesos es cero.

    Example:
        >>> import pandas as pd
        >>> weighted_var(pd.Series([2000.0, 2500.0, 1800.0]), pd.Series([0.5, 0.3, 0.2]))
        69600.0
    """
    w = weights.fillna(0)
    total_w = w.sum()
    if total_w == 0:
        return float("nan")
    mean_w = (values * w).sum() / total_w
    return float((w * (values - mean_w) ** 2).sum())
