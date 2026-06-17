"""Utilidades para formateo y corrección del identificador único de finca (IDFINCA).

El campo IDFINCA debe ser un string de exactamente 7 dígitos con ceros a la
izquierda. Excel corrompe este campo de dos formas:

1. Lo interpreta como número y quita los ceros iniciales (``"0508301"`` → ``"508301"``).
2. Lo convierte a notación científica (``7689510`` → ``"07.69E7"``).

Ambos casos están contemplados en ``format_idfinca``. Las 14 correcciones de
valores incorrectos recurrentes están parametrizadas en ``parameters.yml``
(``idfinca_corrections``) y se aplican con ``apply_idfinca_corrections``.
"""
from __future__ import annotations

import re

import pandas as pd
import structlog

log = structlog.get_logger()


def format_idfinca(raw_val: str) -> str:
    """Convierte un valor raw de IDFINCA a string de 7 dígitos con ceros iniciales.

    Args:
        raw_val: Valor crudo leído del Excel. Puede ser numérico, string,
            notación científica (``'07.69E7'``) o NaN/vacío.

    Returns:
        String de 7 dígitos con ceros iniciales (ej. ``'0508301'``).
        Retorna el valor original sin modificar si es NaN, vacío, tiene notación
        científica o no se puede convertir a entero.

    Raises:
        No lanza excepciones. Los valores no convertibles se registran con warning
        en el log y se devuelven sin cambios.

    Example:
        >>> format_idfinca('508301')
        '0508301'
        >>> format_idfinca(508301.0)
        '0508301'
        >>> format_idfinca('07.69E7')   # notación científica — se deja para corrección
        '07.69E7'
        >>> format_idfinca('')
        ''
    """
    if pd.isna(raw_val) or str(raw_val).strip() == "":
        return raw_val  # type: ignore[return-value]

    cleaned = str(raw_val).strip()

    # Detectar notación científica generada por Excel (ej. '07.69E7', '1.5E6')
    if re.match(r"^[\d.]+[eE]\d+$", cleaned):
        log.warning("idfinca_notacion_cientifica", valor=cleaned)
        return cleaned  # Corregido en apply_idfinca_corrections

    try:
        return str(int(float(cleaned))).zfill(7)
    except (ValueError, OverflowError):
        log.warning("idfinca_no_convertible", valor=cleaned)
        return cleaned


def apply_idfinca_corrections(
    df: pd.DataFrame, corrections: list[dict]
) -> pd.DataFrame:
    """Aplica las correcciones de IDFINCA definidas en ``parameters.yml``.

    Requiere coincidencia simultánea de ``IDFINCA`` Y ``MUNICIPIO`` para evitar
    falsos positivos cuando el mismo valor incorrecto existe en municipios distintos.

    Args:
        df: DataFrame que contiene las columnas ``IDFINCA`` y ``MUNICIPIO``.
        corrections: Lista de dicts con las claves ``wrong``, ``municipio`` y
            ``correct``. Proviene de ``parameters.yml['idfinca_corrections']``.

    Returns:
        Copia del DataFrame con los valores de ``IDFINCA`` corregidos.

    Example:
        >>> import pandas as pd
        >>> df = pd.DataFrame({'IDFINCA': ['0508301', '0515402'],
        ...                    'MUNICIPIO': ['Belmira', 'El Carmen De Viboral']})
        >>> corrections = [
        ...     {'wrong': '0508301', 'municipio': 'Belmira', 'correct': '0508601'},
        ... ]
        >>> apply_idfinca_corrections(df, corrections)['IDFINCA'].tolist()
        ['0508601', '0515402']
    """
    df = df.copy()
    for corr in corrections:
        mask = (df["IDFINCA"] == corr["wrong"]) & (
            df["MUNICIPIO"] == corr["municipio"]
        )
        if mask.any():
            log.info(
                "correccion_idfinca_aplicada",
                wrong=corr["wrong"],
                correct=corr["correct"],
                municipio=corr["municipio"],
                n_registros=int(mask.sum()),
            )
            df.loc[mask, "IDFINCA"] = corr["correct"]
    return df
