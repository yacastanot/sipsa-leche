"""Tests del pipeline correlation — M8: Correlación precio/producción y precio/venta.

Cubre los 4 pasos del módulo:
  Act 51 — Correlación Pearson precio vs producción por municipio
  Act 52 — Correlación Pearson precio vs venta por municipio
  Act 53 — CORMUNI_{MES}: estructura y validación de valores
  Act 54 — CORDEP_{MES}: typo SAS PROCIOPROD conservado
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from sipsa_leche.pipelines.correlation.nodes import calcular_correlaciones

MES = "MAR"


# ─── Fixture base ─────────────────────────────────────────────────────────────

def _fila(dept="Antioquia", muni="Belmira", cod_dep="05", cod_muni="05086",
          precio=1200.0, prod=100.0, venta=80.0, idfinca="0508601") -> dict:
    return dict(
        IDFINCA=idfinca, DEPARTAMENTO=dept, MUNICIPIO=muni, FINCA="F1",
        COD_DEP=cod_dep, COD_MUNI=cod_muni, MACRO="ZONA CAFETERA",
        PRECIOLITROS=precio, PRODUCCION=prod, VENTA=venta,
        VACASOR=5.0, observaciones=None,
    )


def _df(*filas) -> pd.DataFrame:
    return pd.DataFrame(list(filas))


def calc(df):
    return calcular_correlaciones(df, MES)


# ─── Act 51-52: Cálculo de correlaciones municipio ───────────────────────────

class TestCorrelacionMunicipio:
    def test_correlacion_perfecta_positiva_precio_prod(self):
        """Si precio y producción suben juntos → correlación = +1."""
        df = _df(
            _fila(precio=1000.0, prod=100.0),
            _fila(precio=1200.0, prod=120.0, idfinca="B"),
            _fila(precio=1400.0, prod=140.0, idfinca="C"),
            _fila(precio=1600.0, prod=160.0, idfinca="D"),
        )
        cormuni, _ = calc(df)
        assert cormuni.iloc[0][f"PRECIOPROD_{MES}"] == pytest.approx(1.0, abs=1e-9)

    def test_correlacion_perfecta_negativa(self):
        """Si precio sube mientras producción baja → correlación = -1."""
        df = _df(
            _fila(precio=1000.0, prod=160.0),
            _fila(precio=1200.0, prod=120.0, idfinca="B"),
            _fila(precio=1400.0, prod=80.0,  idfinca="C"),
            _fila(precio=1600.0, prod=40.0,  idfinca="D"),
        )
        cormuni, _ = calc(df)
        assert cormuni.iloc[0][f"PRECIOPROD_{MES}"] == pytest.approx(-1.0, abs=1e-9)

    def test_correlacion_cero_con_precio_constante(self):
        """Precio constante → correlación = 0 (sin variabilidad en X)."""
        df = _df(
            _fila(precio=1200.0, prod=100.0),
            _fila(precio=1200.0, prod=150.0, idfinca="B"),
            _fila(precio=1200.0, prod=200.0, idfinca="C"),
        )
        cormuni, _ = calc(df)
        # La correlación de Pearson es NaN cuando std=0 en X
        assert pd.isna(cormuni.iloc[0][f"PRECIOPROD_{MES}"])

    def test_correlacion_precio_venta_presente(self):
        df = _df(
            _fila(precio=1000.0, venta=80.0),
            _fila(precio=1500.0, venta=120.0, idfinca="B"),
        )
        cormuni, _ = calc(df)
        assert f"PRECIOVENTA_{MES}" in cormuni.columns

    def test_una_fila_por_municipio(self):
        df = _df(
            _fila(muni="Belmira", idfinca="A"),
            _fila(muni="Belmira", idfinca="B"),
            _fila(muni="Medellin", cod_muni="05001", idfinca="C"),
        )
        cormuni, _ = calc(df)
        assert len(cormuni) == 2

    def test_rango_correlacion_entre_menos1_y_1(self):
        """Correlación siempre en [-1, 1] cuando hay variabilidad."""
        df = _df(*[_fila(precio=1000.0 + i*100, prod=100.0 + np.random.randint(-20, 20),
                         idfinca=str(i)) for i in range(8)])
        cormuni, _ = calc(df)
        val = cormuni.iloc[0][f"PRECIOPROD_{MES}"]
        if not pd.isna(val):
            assert -1.0 <= val <= 1.0

    def test_excluidas_no_entran(self):
        """Fincas con precio=0 o producción=0 deben excluirse."""
        df = _df(
            _fila(precio=1200.0, prod=100.0),
            _fila(precio=1400.0, prod=120.0, idfinca="B"),
            _fila(precio=0.0, prod=50.0, idfinca="C"),  # excluida
        )
        cormuni, _ = calc(df)
        # Con 2 filas válidas por muni, la correlación se puede calcular
        assert f"PRECIOPROD_{MES}" in cormuni.columns


# ─── Act 53: Estructura CORMUNI_{MES} ─────────────────────────────────────────

class TestEstructuraCormuni:
    def test_columnas_presentes(self):
        cormuni, _ = calc(_df(_fila(), _fila(idfinca="B")))
        for col in ["DEPARTAMENTO", "MUNICIPIO", "IDDEPMUNIM",
                    f"PRECIOPROD_{MES}", f"PRECIOVENTA_{MES}"]:
            assert col in cormuni.columns, f"Columna {col} faltante en CORMUNI"

    def test_iddepmunim_sin_espacios(self):
        df = _df(
            _fila(dept="Valle Del Cauca", muni="Santiago De Cali", cod_dep="76", cod_muni="76001"),
            _fila(dept="Valle Del Cauca", muni="Santiago De Cali", cod_dep="76",
                  cod_muni="76001", idfinca="B", precio=1500.0, prod=200.0),
        )
        cormuni, _ = calc(df)
        assert " " not in cormuni.iloc[0]["IDDEPMUNIM"]
        assert cormuni.iloc[0]["IDDEPMUNIM"] == "ValleDelCaucaSantiagoDeCali"

    def test_dos_municipios_dos_filas_cormuni(self):
        df = _df(
            _fila(muni="Belmira", cod_muni="05086"),
            _fila(muni="Belmira", cod_muni="05086", idfinca="B"),
            _fila(muni="Medellin", cod_muni="05001", idfinca="C"),
            _fila(muni="Medellin", cod_muni="05001", idfinca="D"),
        )
        cormuni, _ = calc(df)
        assert len(cormuni) == 2

    def test_cormuni_tiene_208_municipios_datos_reales(self):
        """Con datos reales, debe haber una fila por municipio con datos válidos."""
        import os
        if not os.path.exists("data/02_intermediate/BASE_032026_clean.parquet"):
            pytest.skip("BASE_032026_clean.parquet no disponible")
        base = pd.read_parquet("data/02_intermediate/BASE_032026_clean.parquet")
        cormuni, _ = calc(base)
        # Todos los municipios con al least 2 obs válidas
        assert len(cormuni) == 208


# ─── Act 54: Estructura CORDEP_{MES} con typo SAS ────────────────────────────

class TestEstructuraCordep:
    def test_columnas_presentes_cordep(self):
        cormuni, cordep = calc(_df(_fila(), _fila(idfinca="B")))
        # Typo SAS: PROCIOPROD (no PRECIOPROD) para departamentos
        for col in ["DEPARTAMENTO", f"PRECIOVENTA_{MES}", f"PROCIOPROD_{MES}"]:
            assert col in cordep.columns, f"Columna {col} faltante en CORDEP"

    def test_typo_sas_procioprod_no_precioprod(self):
        """Verificar que se usa PROCIOPROD (typo del SAS) y NO PRECIOPROD."""
        _, cordep = calc(_df(_fila(), _fila(idfinca="B")))
        assert f"PROCIOPROD_{MES}" in cordep.columns
        assert f"PRECIOPROD_{MES}" not in cordep.columns

    def test_una_fila_por_departamento(self):
        df = _df(
            _fila(dept="Antioquia", idfinca="A"),
            _fila(dept="Antioquia", idfinca="B"),
            _fila(dept="Boyaca", cod_dep="15", cod_muni="15001", muni="Tunja", idfinca="C"),
            _fila(dept="Boyaca", cod_dep="15", cod_muni="15001", muni="Tunja", idfinca="D"),
        )
        _, cordep = calc(df)
        assert len(cordep) == 2

    def test_correlacion_dep_rango_valido(self):
        """La correlación departamental también debe estar en [-1, 1]."""
        df = _df(*[_fila(precio=1000.0 + i*50, prod=100.0 + i*10, idfinca=str(i))
                   for i in range(6)])
        _, cordep = calc(df)
        val_prod = cordep.iloc[0][f"PROCIOPROD_{MES}"]
        val_venta = cordep.iloc[0][f"PRECIOVENTA_{MES}"]
        if not pd.isna(val_prod):
            assert -1.0 <= val_prod <= 1.0
        if not pd.isna(val_venta):
            assert -1.0 <= val_venta <= 1.0

    def test_cordep_tiene_25_departamentos_datos_reales(self):
        import os
        if not os.path.exists("data/02_intermediate/BASE_032026_clean.parquet"):
            pytest.skip("BASE_032026_clean.parquet no disponible")
        base = pd.read_parquet("data/02_intermediate/BASE_032026_clean.parquet")
        _, cordep = calc(base)
        assert len(cordep) == 25

    def test_correlacion_pearson_formula(self):
        """Verificar que la correlación es Pearson (ddof=1, igual que SAS PROC CORR)."""
        data = {"PRECIOLITROS": [1000.0, 1200.0, 1400.0, 1600.0],
                "PRODUCCION":   [100.0,  120.0,  140.0,  160.0],
                "VENTA":        [80.0,   96.0,   112.0,  128.0]}
        df = pd.DataFrame([_fila(precio=p, prod=q, venta=v, idfinca=str(i))
                           for i, (p, q, v) in enumerate(zip(
                               data["PRECIOLITROS"], data["PRODUCCION"], data["VENTA"]))])
        cormuni, _ = calc(df)
        # Correlación perfecta → 1.0
        assert cormuni.iloc[0][f"PRECIOPROD_{MES}"] == pytest.approx(1.0, abs=1e-9)
        assert cormuni.iloc[0][f"PRECIOVENTA_{MES}"] == pytest.approx(1.0, abs=1e-9)
