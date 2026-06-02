"""Tests del pipeline dept_macro_price — M6: Precio por departamento y macrorregión.

Cubre los 7 pasos del módulo:
  Act 37 — ME_PRECIO_DEP ponderada por litros producidos
  Act 38 — SDPRECIO_DEP + PON_NAL por departamento
  Act 39 — Acumulados: TVACAS, TPROD, MEPROD, SDPROD, TVENTA, MEVENTA, SDVENTA
  Act 40 — ME_PRECIO_MACRO ponderada por litros en las 5 macrorregiones
  Act 41 — SD_PRECIO_MACRO + acumulados de macro + PON_NACIONAL
  Act 43 — Regresión numérica vs hojas DEPARTAMENTO y MACROREGION de CUADROS_032026_TOT
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from sipsa_leche.pipelines.dept_macro_price.nodes import (
    calcular_precio_departamento,
    calcular_precio_macro,
)

MES = "MAR"

# ─── Fixture base ─────────────────────────────────────────────────────────────

def _fila(dept="Antioquia", muni="Belmira", finca="F1",
          cod_dep="05", cod_muni="05086", macro="ZONA CAFETERA",
          precio=1200.0, prod=100.0, venta=80.0, vacas=5.0,
          idfinca="0508601", **kw) -> dict:
    return dict(
        IDFINCA=idfinca, DEPARTAMENTO=dept, MUNICIPIO=muni, FINCA=finca,
        COD_DEP=cod_dep, COD_MUNI=cod_muni, MACRO=macro,
        PRECIOLITROS=precio, PRODUCCION=prod, VENTA=venta, VACASOR=vacas,
        observaciones=None, **kw
    )


def _df(*filas) -> pd.DataFrame:
    return pd.DataFrame(list(filas))


def calc_dept(df):
    return calcular_precio_departamento(df, MES)


def calc_macro(df):
    return calcular_precio_macro(df, MES)


# ─── Acts 37-38: ME_PRECIO_DEP y SDPRECIO_DEP ─────────────────────────────────

class TestMePrecioDep:
    def test_precio_constante_me_igual_precio(self):
        df = _df(
            _fila(precio=1500.0, prod=200.0),
            _fila(idfinca="B", finca="F2", precio=1500.0, prod=300.0),
        )
        out = calc_dept(df)
        assert out.iloc[0][f"ME_PRECIO_DEP_{MES}"] == pytest.approx(1500.0, rel=1e-6)

    def test_me_precio_ponderada_por_produccion(self):
        """F1: 1000 × 300 (60%) + F2: 2000 × 200 (40%) = 1400."""
        df = _df(
            _fila(precio=1000.0, prod=300.0),
            _fila(idfinca="B", finca="F2", precio=2000.0, prod=200.0),
        )
        out = calc_dept(df)
        assert out.iloc[0][f"ME_PRECIO_DEP_{MES}"] == pytest.approx(1400.0, rel=1e-6)

    def test_sd_precio_dep_cero_con_precio_constante(self):
        df = _df(
            _fila(precio=1500.0, prod=200.0),
            _fila(idfinca="B", finca="F2", precio=1500.0, prod=300.0),
        )
        out = calc_dept(df)
        assert out.iloc[0][f"SDPRECIO_DEP_{MES}"] == pytest.approx(0.0, abs=1e-9)

    def test_sd_precio_dep_formula_ponderada(self):
        """F1: 1000, prod=100 (50%) — F2: 2000, prod=100 (50%) — SD = 500."""
        df = _df(
            _fila(precio=1000.0, prod=100.0),
            _fila(idfinca="B", finca="F2", precio=2000.0, prod=100.0),
        )
        out = calc_dept(df)
        assert out.iloc[0][f"SDPRECIO_DEP_{MES}"] == pytest.approx(500.0, rel=1e-6)

    def test_una_fila_por_departamento(self):
        df = _df(*[_fila(idfinca=str(i), finca=f"F{i}") for i in range(6)])
        out = calc_dept(df)
        assert len(out) == 1

    def test_dos_departamentos_dos_filas(self):
        df = _df(
            _fila(dept="Antioquia", cod_dep="05"),
            _fila(dept="Boyaca", cod_dep="15", cod_muni="15001"),
        )
        out = calc_dept(df)
        assert len(out) == 2


# ─── Act 38: PON_NAL ──────────────────────────────────────────────────────────

class TestPonNalDep:
    def test_pon_nal_suma_1(self):
        df = _df(
            _fila(dept="Antioquia", cod_dep="05", prod=400.0),
            _fila(dept="Boyaca",    cod_dep="15", cod_muni="15001", prod=600.0),
        )
        out = calc_dept(df)
        assert out[f"PON_NAL_{MES}"].sum() == pytest.approx(1.0, rel=1e-9)

    def test_pon_nal_proporcional_produccion(self):
        """Antioquia 30%, Boyacá 70%."""
        df = _df(
            _fila(dept="Antioquia", cod_dep="05", prod=300.0),
            _fila(dept="Boyaca",    cod_dep="15", cod_muni="15001", prod=700.0),
        )
        out = calc_dept(df).sort_values("DEPARTAMENTO").reset_index(drop=True)
        assert out.iloc[0][f"PON_NAL_{MES}"] == pytest.approx(0.30, rel=1e-6)
        assert out.iloc[1][f"PON_NAL_{MES}"] == pytest.approx(0.70, rel=1e-6)


# ─── Act 39: Acumulados por departamento ──────────────────────────────────────

class TestAcumuladosDep:
    def test_tprod_es_suma_total(self):
        df = _df(_fila(prod=300.0), _fila(idfinca="B", finca="F2", prod=200.0))
        out = calc_dept(df)
        assert out.iloc[0][f"TPROD_DEP_{MES}"] == pytest.approx(500.0)

    def test_tvacas_es_suma_semanal(self):
        df = _df(_fila(vacas=10.0), _fila(idfinca="B", finca="F2", vacas=15.0))
        out = calc_dept(df)
        assert out.iloc[0][f"TVACAS_DEP_{MES}"] == pytest.approx(25.0)

    def test_tventa_es_suma_semanal(self):
        df = _df(_fila(venta=80.0), _fila(idfinca="B", finca="F2", venta=100.0))
        out = calc_dept(df)
        assert out.iloc[0][f"TVENTA_DEP_{MES}"] == pytest.approx(180.0)

    def test_columnas_dinamicas_presentes(self):
        out = calc_dept(_df(_fila()))
        for col in [
            f"MINPRECIO_DEP_{MES}", f"MAXPRECIO_DEP_{MES}", f"ME_PRECIO_DEP_{MES}",
            f"SDPRECIO_DEP_{MES}", f"TPROD_DEP_{MES}", f"MEPROD_DEP_{MES}",
            f"SDPROD_DEP_{MES}", f"MEVACAS_DEP_{MES}", f"TVACAS_DEP_{MES}",
            f"TVENTA_DEP_{MES}", f"MEVENTA_DEP_{MES}", f"SDVENTA_DEP_{MES}",
            f"PON_NAL_{MES}",
        ]:
            assert col in out.columns, f"Columna {col} faltante"

    def test_excluidas_no_entran(self):
        df = _df(
            _fila(precio=1200.0, prod=100.0),
            _fila(idfinca="B", finca="F2", precio=0.0, prod=100.0),
        )
        out = calc_dept(df)
        assert out.iloc[0][f"TPROD_DEP_{MES}"] == pytest.approx(100.0)


# ─── Acts 40-41: Precio por macrorregión ──────────────────────────────────────

class TestMePrecioMacro:
    def test_precio_constante_me_igual_precio(self):
        df = _df(
            _fila(precio=1500.0, prod=200.0, macro="ZONA CAFETERA"),
            _fila(idfinca="B", finca="F2", precio=1500.0, prod=300.0, macro="ZONA CAFETERA"),
        )
        out = calc_macro(df)
        row = out[out["MACRO"] == "ZONA CAFETERA"].iloc[0]
        assert row[f"ME_PRECIO_MACRO{MES}"] == pytest.approx(1500.0, rel=1e-6)

    def test_me_precio_macro_ponderada(self):
        """F1: 1000×300 (60%) + F2: 2000×200 (40%) = 1400."""
        df = _df(
            _fila(precio=1000.0, prod=300.0, macro="ZONA CAFETERA"),
            _fila(idfinca="B", finca="F2", precio=2000.0, prod=200.0, macro="ZONA CAFETERA"),
        )
        out = calc_macro(df)
        row = out[out["MACRO"] == "ZONA CAFETERA"].iloc[0]
        assert row[f"ME_PRECIO_MACRO{MES}"] == pytest.approx(1400.0, rel=1e-6)

    def test_sd_precio_macro_cero_con_precio_constante(self):
        df = _df(
            _fila(precio=1500.0, prod=200.0, macro="ZONA CAFETERA"),
            _fila(idfinca="B", finca="F2", precio=1500.0, prod=300.0, macro="ZONA CAFETERA"),
        )
        out = calc_macro(df)
        row = out[out["MACRO"] == "ZONA CAFETERA"].iloc[0]
        assert row[f"SD_PRECIO_MACRO{MES}"] == pytest.approx(0.0, abs=1e-9)

    def test_naming_sin_guion_antes_mes(self):
        """Naming SAS: MINPRECIO_MACROMAR (no MINPRECIO_MACRO_MAR)."""
        out = calc_macro(_df(_fila()))
        assert f"MINPRECIO_MACRO{MES}" in out.columns
        assert f"ME_PRECIO_MACRO{MES}" in out.columns
        assert f"PON_NACIONAL{MES}" in out.columns
        # Verificar que NO hay columnas con doble guión
        assert f"MINPRECIO_MACRO_{MES}" not in out.columns

    def test_cinco_macros_si_hay_datos_en_todas(self):
        macros = [
            "ZONA CAFETERA", "BOYACA Y CUNDINAMARCA",
            "COSTA ATLANTICA", "CAUCA,NARIÑO Y VALLE DEL CAUCA ",
            "RESTO",
        ]
        filas = [_fila(macro=mac, idfinca=f"000000{i}") for i, mac in enumerate(macros)]
        out = calc_macro(_df(*filas))
        assert len(out) == 5

    def test_filas_sin_macro_excluidas(self):
        """Fincas con MACRO=None no entran al cálculo."""
        df = _df(
            _fila(macro="ZONA CAFETERA", prod=100.0),
            _fila(idfinca="B", finca="F2", macro=None, prod=50.0),
        )
        out = calc_macro(df)
        assert len(out) == 1

    def test_columnas_dinamicas_macro(self):
        out = calc_macro(_df(_fila()))
        for col in [
            f"MINPRECIO_MACRO{MES}", f"MAXPRECIO_MACRO{MES}",
            f"ME_PRECIO_MACRO{MES}", f"SD_PRECIO_MACRO{MES}",
            f"T_VACAS_MACRO{MES}", f"ME_PRODUCCION_MACRO{MES}",
            f"T_PRODUCCION_MACRO{MES}", f"SD_PRODUCCION_MACRO{MES}",
            f"T_VENTA_MACRO{MES}", f"PON_NACIONAL{MES}",
        ]:
            assert col in out.columns, f"Columna {col} faltante"


class TestPonNacionalMacro:
    def test_pon_nacional_suma_1(self):
        macros = [
            "ZONA CAFETERA", "BOYACA Y CUNDINAMARCA",
            "COSTA ATLANTICA", "CAUCA,NARIÑO Y VALLE DEL CAUCA ", "RESTO",
        ]
        filas = [_fila(macro=mac, idfinca=f"000000{i}", prod=float(100 * (i+1)))
                 for i, mac in enumerate(macros)]
        out = calc_macro(_df(*filas))
        assert out[f"PON_NACIONAL{MES}"].sum() == pytest.approx(1.0, rel=1e-9)


# ─── Act 43: Regresión numérica vs referencia SAS ────────────────────────────

RUTA_REF = (
    r"C:\Users\Jeferson\OneDrive - Cloud Integration Hub"
    r"\Documentos\DANE Automatización\SIPSA Leche"
    r"\CUADROS_032026_TOT.xls.xlsx"
)
RUTA_CLEAN = "data/02_intermediate/BASE_032026_clean.parquet"
TOL_REL = 1e-4


@pytest.mark.regression
class TestRegressionDepartamento:
    @pytest.fixture(scope="class")
    def ref(self):
        import os
        if not os.path.exists(RUTA_REF):
            pytest.skip("Referencia SAS no disponible")
        df = pd.read_excel(RUTA_REF, sheet_name="DEPARTAMENTO", dtype=str)
        for col in ["ME_PRECIO_DEP_MAR", "SDPRECIO_DEP_MAR", "TPROD_DEP_MAR", "PON_NAL_MAR"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        return df

    @pytest.fixture(scope="class")
    def resultado(self):
        import os
        if not os.path.exists(RUTA_CLEAN):
            pytest.skip("BASE_032026_clean.parquet no disponible")
        return calcular_precio_departamento(pd.read_parquet(RUTA_CLEAN), "MAR")

    def test_numero_departamentos(self, ref, resultado):
        assert len(resultado) == len(ref), f"Deptos: Python={len(resultado)}, Ref={len(ref)}"

    def test_me_precio_dep_dentro_tolerancia(self, ref, resultado):
        merged = resultado.merge(
            ref[["DEPARTAMENTO", "ME_PRECIO_DEP_MAR"]].rename(columns={"ME_PRECIO_DEP_MAR": "REF"}),
            on="DEPARTAMENTO", how="inner"
        )
        diff = ((merged["ME_PRECIO_DEP_MAR"] - merged["REF"]).abs() /
                merged["REF"].replace(0, np.nan)).dropna()
        assert (diff > TOL_REL).sum() == 0, f"Max diff: {diff.max():.2e}"

    def test_tprod_dep_exacto(self, ref, resultado):
        merged = resultado.merge(
            ref[["DEPARTAMENTO", "TPROD_DEP_MAR"]].rename(columns={"TPROD_DEP_MAR": "REF"}),
            on="DEPARTAMENTO", how="inner"
        )
        np.testing.assert_allclose(
            merged["TPROD_DEP_MAR"].values, merged["REF"].values, rtol=1e-9,
        )

    def test_pon_nal_suma_1(self, resultado):
        assert abs(resultado[f"PON_NAL_{MES}"].sum() - 1.0) < 1e-9


@pytest.mark.regression
class TestRegressionMacro:
    @pytest.fixture(scope="class")
    def ref(self):
        import os
        if not os.path.exists(RUTA_REF):
            pytest.skip("Referencia SAS no disponible")
        df = pd.read_excel(RUTA_REF, sheet_name="MACROREGION", dtype=str)
        for col in ["ME_PRECIO_MACROMAR", "SD_PRECIO_MACROMAR",
                    "T_PRODUCCION_MACROMAR", "PON_NACIONALMAR"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        return df[df["MACRO"].notna()]   # excluir fila de total/nulos si existe

    @pytest.fixture(scope="class")
    def resultado(self):
        import os
        if not os.path.exists(RUTA_CLEAN):
            pytest.skip("BASE_032026_clean.parquet no disponible")
        return calcular_precio_macro(pd.read_parquet(RUTA_CLEAN), "MAR")

    def test_cinco_macroregiones(self, resultado):
        assert len(resultado) == 5

    def test_me_precio_macro_dentro_tolerancia(self, ref, resultado):
        merged = resultado.merge(
            ref[["MACRO", "ME_PRECIO_MACROMAR"]].rename(columns={"ME_PRECIO_MACROMAR": "REF"}),
            on="MACRO", how="inner"
        )
        diff = ((merged["ME_PRECIO_MACROMAR"] - merged["REF"]).abs() /
                merged["REF"].replace(0, np.nan)).dropna()
        assert (diff > TOL_REL).sum() == 0, f"Max diff macro: {diff.max():.2e}"

    def test_t_produccion_macro_exacto(self, ref, resultado):
        merged = resultado.merge(
            ref[["MACRO", "T_PRODUCCION_MACROMAR"]].rename(columns={"T_PRODUCCION_MACROMAR": "REF"}),
            on="MACRO", how="inner"
        )
        np.testing.assert_allclose(
            merged["T_PRODUCCION_MACROMAR"].values, merged["REF"].values, rtol=1e-9,
        )

    def test_pon_nacional_suma_1(self, resultado):
        assert abs(resultado[f"PON_NACIONAL{MES}"].sum() - 1.0) < 1e-6
