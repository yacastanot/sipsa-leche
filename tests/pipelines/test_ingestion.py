"""Tests del pipeline ingestion — M2 Act 5: Lectura del Excel de finca."""
from __future__ import annotations

import pandas as pd
import pandera.errors
import pytest

from sipsa_leche.pipelines.ingestion.nodes import snapshot_raw


def _make_raw(**overrides) -> pd.DataFrame:
    row = {
        "IDFINCA": "0508601",
        "MUNICIPIO": "BELMIRA",
        "DEPARTAMENTO": "ANTIOQUIA",
        "FINCA": "LA ESPERANZA",
        "VACASOR": "5",
        "PRECIOLITROS": "1200",
        "PRODUCCION": "100",
        "VENTA": "80",
    }
    row.update(overrides)
    return pd.DataFrame([row])


def test_snapshot_raw_retorna_dataframe_identico():
    df = _make_raw()
    result = snapshot_raw(df)
    pd.testing.assert_frame_equal(result, df)


def test_snapshot_raw_falla_sin_idfinca():
    df = _make_raw()
    df = df.drop(columns=["IDFINCA"])
    with pytest.raises(Exception):
        snapshot_raw(df)


def test_snapshot_raw_acepta_numericos_nulos():
    df = _make_raw(VACASOR=None, PRECIOLITROS=None, PRODUCCION=None, VENTA=None)
    result = snapshot_raw(df)
    assert len(result) == 1


def test_snapshot_raw_preserva_idfinca_como_string():
    df = _make_raw(IDFINCA="0508601")
    result = snapshot_raw(df)
    assert result["IDFINCA"].dtype == object
