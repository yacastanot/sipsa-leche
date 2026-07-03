"""Tests del pipeline outputs — M10: Cuadros de salida para publicacion."""
import numpy as np
import pandas as pd
import pytest
from unittest.mock import patch
from pathlib import Path

from sipsa_leche.pipelines.outputs.nodes import (
    generar_cuadros_salida,
    _preparar_finca,
    _select,
    _cols_muni_tot,
    _cols_muni_pub,
)

MES_A, MES_ANT, PER = "MAR", "FEB", "032026"

def _var_finca():
    return pd.DataFrame([{
        "IDFINCA": "0508601", "IDFINCA_AUX_MAR": "ABF1",
        "DEPARTAMENTO_MAR": "Antioquia", "MUNICIPIO_MAR": "Belmira",
        "FINCA_MAR": "F1", "COD_DEP_MAR": "05", "COD_MUNI_MAR": "05086",
        "DEPARTAMENTO_FEB": "Antioquia", "MUNICIPIO_FEB": "Belmira",
        "FINCA_FEB": "F1", "COD_DEP_FEB": "05", "COD_MUNI_FEB": "05086",
        "IDFINCA_AUX_FEB": "ABF1",
        "MED_FINCA_FEB": 1200.0, "T_PROD_FEB": 400.0, "T_VACAS_FEB": 5.0,
        "T_VENTA_FEB": 320.0, "MIN_PRECIO_FEB": 1150.0, "MAX_PRECIO_FEB": 1250.0,
        "VAR_FINCA_FEB": 100.0, "PONMUNI_FEB": 0.5,
        "MED_FINCA_MAR": 1250.0, "T_PROD_MAR": 420.0, "T_VACAS_MAR": 5.0,
        "T_VENTA_MAR": 335.0, "MIN_PRECIO_MAR": 1200.0, "MAX_PRECIO_MAR": 1300.0,
        "VAR_FINCA_MAR": 110.0, "PONMUNI_MAR": 0.5,
        "VPRE_MARFEB": 0.0416, "VPROD_FEBMAR": 0.05, "TENDENCIA_PRECIO": "°",
    }])

def _var_muni():
    return pd.DataFrame([{
        "DEPARTAMENTO": "Antioquia", "MUNICIPIO": "Belmira",
        "COD_DEP": "05", "COD_MUNI": "05086", "IDDEPMUNI": "AntioquiaBelmira",
        "ME_PRECIO_MUNI_FEB": 1200.0, "SD_PRECIO_MUNI_FEB": 60.0,
        "CV_PRECIO_MUNI_FEB": 0.05, "MINPRECIO_MUNI_FEB": 1100.0,
        "MAXPRECIO_MUNI_FEB": 1300.0, "T_VACAS_MUNI_FEB": 50.0,
        "ME_PRODUCCION_MUNI_FEB": 500.0, "T_PRODUCCION_MUNI_FEB": 2000.0,
        "SD_PRODUCCION_MUNI_FEB": 100.0, "T_VENTA_MUNI_FEB": 1800.0,
        "PON_NACIONAL_FEB": 0.10, "PRODDEP_FEB": 10000.0, "PONDEPMUNI_FEB": 0.20,
        "ME_PRECIO_MUNI_MAR": 1250.0, "SD_PRECIO_MUNI_MAR": 62.0,
        "CV_PRECIO_MUNI_MAR": 0.05, "MINPRECIO_MUNI_MAR": 1150.0,
        "MAXPRECIO_MUNI_MAR": 1350.0, "T_VACAS_MUNI_MAR": 52.0,
        "ME_PRODUCCION_MUNI_MAR": 510.0, "T_PRODUCCION_MUNI_MAR": 2040.0,
        "SD_PRODUCCION_MUNI_MAR": 102.0, "T_VENTA_MUNI_MAR": 1836.0,
        "PON_NACIONAL_MAR": 0.10, "PRODDEP_MAR": 10200.0, "PONDEPMUNI_MAR": 0.20,
        "VPRE_FEBMAR": 0.0416, "VPROD_FEBMAR": 0.02, "TENDENCIA_PRECIO": "°",
    }])

def _var_dep():
    return pd.DataFrame([{
        "DEPARTAMENTO": "Antioquia", "COD_DEP": "05",
        "MINPRECIO_DEP_FEB": 1100.0, "MAXPRECIO_DEP_FEB": 1300.0,
        "ME_PRECIO_DEP_FEB": 1200.0, "SDPRECIO_DEP_FEB": 60.0, "CV_PRECIO_DEP_FEB": 0.05,
        "TPROD_DEP_FEB": 20000.0, "MEPROD_DEP_FEB": 500.0, "SDPROD_DEP_FEB": 100.0,
        "MEVACAS_DEP_FEB": 25.0, "TVACAS_DEP_FEB": 100.0,
        "TVENTA_DEP_FEB": 18000.0, "MEVENTA_DEP_FEB": 450.0, "SDVENTA_DEP_FEB": 50.0,
        "PON_NAL_FEB": 0.16,
        "MINPRECIO_DEP_MAR": 1150.0, "MAXPRECIO_DEP_MAR": 1350.0,
        "ME_PRECIO_DEP_MAR": 1250.0, "SDPRECIO_DEP_MAR": 62.0, "CV_PRECIO_DEP_MAR": 0.05,
        "TPROD_DEP_MAR": 20400.0, "MEPROD_DEP_MAR": 510.0, "SDPROD_DEP_MAR": 102.0,
        "MEVACAS_DEP_MAR": 25.5, "TVACAS_DEP_MAR": 102.0,
        "TVENTA_DEP_MAR": 18360.0, "MEVENTA_DEP_MAR": 459.0, "SDVENTA_DEP_MAR": 51.0,
        "PON_NAL_MAR": 0.16,
        "VPRE_FEBMAR": 0.0416, "VPROD_FEBMAR": 0.02, "TENDENCIA_PRECIO": "°",
    }])

def _var_mac():
    return pd.DataFrame([{
        "MACRO": "ZONA CAFETERA",
        "MINPRECIO_MACROFEB": 1100.0, "MAXPRECIO_MACROFEB": 1400.0,
        "ME_PRECIO_MACROFEB": 1200.0, "SD_PRECIO_MACROFEB": 80.0, "CV_PRECIO_MACROFEB": 0.07,
        "T_VACAS_MACROFEB": 1000.0, "ME_PRODUCCION_MACROFEB": 2000.0,
        "T_PRODUCCION_MACROFEB": 500000.0, "SD_PRODUCCION_MACROFEB": 300.0,
        "T_VENTA_MACROFEB": 450000.0, "PON_NACIONALFEB": 0.30,
        "MINPRECIO_MACROMAR": 1150.0, "MAXPRECIO_MACROMAR": 1450.0,
        "ME_PRECIO_MACROMAR": 1250.0, "SD_PRECIO_MACROMAR": 82.0, "CV_PRECIO_MACROMAR": 0.07,
        "T_VACAS_MACROMAR": 1010.0, "ME_PRODUCCION_MACROMAR": 2020.0,
        "T_PRODUCCION_MACROMAR": 510000.0, "SD_PRODUCCION_MACROMAR": 305.0,
        "T_VENTA_MACROMAR": 459000.0, "PON_NACIONALMAR": 0.30,
        "VPRE_FEBMAR": 0.0416, "VPROD_FEBMAR": 0.02, "TENDENCIA_PRECIO": "°",
    }])

def _var_cob():
    return pd.DataFrame([{
        "DEPARTAMENTO": "Antioquia", "COD_MUNI": "05086",
        "MUNICIPIO": "Belmira", "IDDEPMUNI": "AntioquiaBelmira",
        "VMAR": 10.0, "NOMAR": 1.0, "VFEB": 10.0,
        "D1_MARFEB": 0.0, "D2_MARFEB": 0.0,
    }])


class TestPrepararFinca:
    def test_reconstruye_departamento(self):
        df = _preparar_finca(_var_finca(), "FEB", "MAR")
        assert "DEPARTAMENTO" in df.columns
        assert df.iloc[0]["DEPARTAMENTO"] == "Antioquia"

    def test_reconstruye_idfinca_aux(self):
        df = _preparar_finca(_var_finca(), "FEB", "MAR")
        assert "IDFINCA_AUX" in df.columns

    def test_columnas_mes_especifico_preservadas(self):
        df = _preparar_finca(_var_finca(), "FEB", "MAR")
        assert "MED_FINCA_FEB" in df.columns
        assert "MED_FINCA_MAR" in df.columns


class TestSelectCols:
    def test_selecciona_subset(self):
        df = _var_muni()
        cols = _cols_muni_tot("FEB", "MAR")
        result = _select(df, cols)
        assert set(result.columns) <= set(cols)

    def test_ignora_faltantes_sin_error(self):
        df = pd.DataFrame([{"DEPARTAMENTO": "A", "MUNICIPIO": "B"}])
        result = _select(df, ["DEPARTAMENTO", "MUNICIPIO", "NO_EXISTE"])
        assert "DEPARTAMENTO" in result.columns
        assert "NO_EXISTE" not in result.columns

    def test_muni_pub_menos_cols_que_tot(self):
        tot = _cols_muni_tot("FEB", "MAR")
        pub = _cols_muni_pub("FEB", "MAR")
        assert len(pub) < len(tot)


class TestGenerar:
    def test_retorna_log_dataframe(self, tmp_path, monkeypatch):
        import sipsa_leche.pipelines.outputs.nodes as m
        calls = []
        def mock_write(path, sheets):
            calls.append(path)
        monkeypatch.setattr(m, "_write_excel", mock_write)
        # Patch Path constructor to use tmp_path
        log_df = generar_cuadros_salida(
            _var_finca(), _var_muni(), _var_dep(), _var_mac(), _var_cob(),
            "MAR", "FEB", "032026",
        )
        assert len(log_df) == 1
        assert log_df.iloc[0]["periodo"] == "032026"
        assert log_df.iloc[0]["municipios"] == 1

    def test_escribe_tres_archivos(self, monkeypatch):
        import sipsa_leche.pipelines.outputs.nodes as m
        calls = []
        def mock_write(path, sheets):
            calls.append(str(path))
        monkeypatch.setattr(m, "_write_excel", mock_write)
        generar_cuadros_salida(
            _var_finca(), _var_muni(), _var_dep(), _var_mac(), _var_cob(),
            "MAR", "FEB", "032026",
        )
        assert len(calls) == 3
        assert any("TOT" in c for c in calls)
        assert any("COBERTURA" in c for c in calls)
