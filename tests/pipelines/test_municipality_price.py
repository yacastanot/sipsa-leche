"""Tests del pipeline municipality_price — M5: Precio medio del litro por municipio.

Cubre los 6 pasos del módulo:
  Act 30 — T_PRODUCCION_MUNI, MIN/MAX precio
  Act 31 — ME_PRECIO_MUNI = media ponderada por litros producidos
  Act 32 — SD_PRECIO_MUNI = desviación estándar ponderada
  Act 33 — PON_NACIONAL = participación del municipio en la producción nacional
  Act 34 — PRODDEP + PONDEPMUNI = participación del municipio en el departamento
  Act 35 — Columnas sufijadas con mes_actual
  Act 36 — Regresión numérica: diferencia < 0.01% vs referencia SAS BASE032026
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from sipsa_leche.pipelines.municipality_price.nodes import calcular_precio_municipio

MES = "MAR"


# ─── Fixture base ─────────────────────────────────────────────────────────────

def _fila(muni="Belmira", dept="Antioquia", cod_muni="05086", cod_dep="05",
           precio=1200.0, prod=100.0, venta=80.0, vacas=5.0,
           idfinca="0508601", finca="F1", **kw) -> dict:
    return dict(
        IDFINCA=idfinca, DEPARTAMENTO=dept, MUNICIPIO=muni, FINCA=finca,
        COD_DEP=cod_dep, COD_MUNI=cod_muni,
        PRECIOLITROS=precio, PRODUCCION=prod, VENTA=venta, VACASOR=vacas,
        observaciones=None, MACRO="ZONA CAFETERA", **kw
    )


def _df(*filas) -> pd.DataFrame:
    return pd.DataFrame(list(filas))


def calc(df):
    return calcular_precio_municipio(df, MES)


# ─── Act 30: T_PRODUCCION_MUNI, MIN/MAX precio ───────────────────────────────

class TestProduccionMinMax:
    def test_t_produccion_muni_es_suma_total(self):
        df = _df(
            _fila(idfinca="A", prod=300.0),
            _fila(idfinca="A", prod=200.0),   # misma finca semana 2
            _fila(idfinca="B", finca="F2", prod=500.0),
        )
        out = calc(df)
        assert out.iloc[0][f"T_PRODUCCION_MUNI_{MES}"] == pytest.approx(1000.0)

    def test_min_precio_muni_es_minimo(self):
        df = _df(_fila(precio=1000.0), _fila(precio=1500.0), _fila(precio=1200.0))
        out = calc(df)
        assert out.iloc[0][f"MINPRECIO_MUNI_{MES}"] == pytest.approx(1000.0)

    def test_max_precio_muni_es_maximo(self):
        df = _df(_fila(precio=1000.0), _fila(precio=1500.0), _fila(precio=1200.0))
        out = calc(df)
        assert out.iloc[0][f"MAXPRECIO_MUNI_{MES}"] == pytest.approx(1500.0)

    def test_excluidas_no_entran_al_calculo(self):
        df = _df(
            _fila(idfinca="A", precio=1200.0, prod=100.0),
            _fila(idfinca="B", finca="F2", precio=0.0, prod=50.0),   # excluida
        )
        out = calc(df)
        assert out.iloc[0][f"T_PRODUCCION_MUNI_{MES}"] == pytest.approx(100.0)
        assert len(out) == 1

    def test_una_fila_por_municipio(self):
        """4 semanas de 3 fincas en el mismo municipio → 1 fila."""
        filas = [_fila(idfinca="A")] * 4 + [_fila(idfinca="B", finca="F2")] * 4
        df = _df(*filas)
        out = calc(df)
        assert len(out) == 1


# ─── Act 31: ME_PRECIO_MUNI — media ponderada ─────────────────────────────────

class TestMePrecioMuni:
    def test_precio_constante_me_igual_precio(self):
        df = _df(
            _fila(idfinca="A", precio=1500.0, prod=200.0),
            _fila(idfinca="B", finca="F2", precio=1500.0, prod=300.0),
        )
        out = calc(df)
        assert out.iloc[0][f"ME_PRECIO_MUNI_{MES}"] == pytest.approx(1500.0, rel=1e-6)

    def test_me_precio_ponderada_por_produccion(self):
        """F1: 1000 COP × 300 litros (60%) + F2: 2000 COP × 200 litros (40%) = 1400 COP."""
        df = _df(
            _fila(idfinca="A", precio=1000.0, prod=300.0),
            _fila(idfinca="B", finca="F2", precio=2000.0, prod=200.0),
        )
        out = calc(df)
        assert out.iloc[0][f"ME_PRECIO_MUNI_{MES}"] == pytest.approx(1400.0, rel=1e-6)

    def test_me_precio_4_semanas_misma_finca(self):
        """4 semanas con mismo precio → ME = ese precio."""
        filas = [_fila(precio=1800.0, prod=100.0)] * 4
        df = _df(*filas)
        out = calc(df)
        assert out.iloc[0][f"ME_PRECIO_MUNI_{MES}"] == pytest.approx(1800.0, rel=1e-6)

    def test_me_precio_col_existe(self):
        df = _df(_fila())
        out = calc(df)
        assert f"ME_PRECIO_MUNI_{MES}" in out.columns


# ─── Act 32: SD_PRECIO_MUNI — desviación estándar ponderada ──────────────────

class TestSdPrecioMuni:
    def test_sd_cero_cuando_precio_constante(self):
        df = _df(
            _fila(idfinca="A", precio=1500.0, prod=200.0),
            _fila(idfinca="B", finca="F2", precio=1500.0, prod=300.0),
        )
        out = calc(df)
        assert out.iloc[0][f"SD_PRECIO_MUNI_{MES}"] == pytest.approx(0.0, abs=1e-9)

    def test_sd_positiva_con_precios_distintos(self):
        df = _df(
            _fila(idfinca="A", precio=1000.0, prod=100.0),
            _fila(idfinca="B", finca="F2", precio=2000.0, prod=100.0),
        )
        out = calc(df)
        assert out.iloc[0][f"SD_PRECIO_MUNI_{MES}"] > 0

    def test_sd_formula_ponderada(self):
        """F1: 1000, prod=100 (50%) — F2: 2000, prod=100 (50%)
        ME = 1500; VAR_Y = 0.5*(1000-1500)^2 + 0.5*(2000-1500)^2 = 250000
        SD = sqrt(250000) = 500."""
        df = _df(
            _fila(idfinca="A", precio=1000.0, prod=100.0),
            _fila(idfinca="B", finca="F2", precio=2000.0, prod=100.0),
        )
        out = calc(df)
        assert out.iloc[0][f"SD_PRECIO_MUNI_{MES}"] == pytest.approx(500.0, rel=1e-6)


# ─── Act 33: PON_NACIONAL ─────────────────────────────────────────────────────

class TestPonNacional:
    def test_pon_nacional_suma_1_en_todo_el_pais(self):
        """PON_NACIONAL de todos los municipios debe sumar exactamente 1."""
        df = _df(
            _fila(muni="Belmira",  cod_muni="05086", idfinca="A", prod=300.0),
            _fila(muni="Medellin", cod_muni="05001", idfinca="B", prod=700.0),
        )
        out = calc(df)
        assert out[f"PON_NACIONAL_{MES}"].sum() == pytest.approx(1.0, rel=1e-9)

    def test_pon_nacional_proporcional_a_produccion(self):
        """Municipio A produce 30%, municipio B produce 70%."""
        df = _df(
            _fila(muni="A", cod_muni="05001", idfinca="X", prod=300.0),
            _fila(muni="B", cod_muni="05002", idfinca="Y", prod=700.0),
        )
        out = calc(df).sort_values("MUNICIPIO").reset_index(drop=True)
        assert out.iloc[0][f"PON_NACIONAL_{MES}"] == pytest.approx(0.30, rel=1e-6)
        assert out.iloc[1][f"PON_NACIONAL_{MES}"] == pytest.approx(0.70, rel=1e-6)

    def test_pon_nacional_col_existe(self):
        out = calc(_df(_fila()))
        assert f"PON_NACIONAL_{MES}" in out.columns


# ─── Act 34: PONDEPMUNI ───────────────────────────────────────────────────────

class TestPondepMuni:
    def test_pondepmuni_suma_1_por_departamento(self):
        """Todos los municipios de un dpto suman PONDEPMUNI = 1."""
        df = _df(
            _fila(muni="Belmira",  cod_muni="05086", idfinca="A", prod=400.0),
            _fila(muni="Medellin", cod_muni="05001", idfinca="B", prod=600.0),
        )
        out = calc(df)
        assert out.groupby("DEPARTAMENTO")[f"PONDEPMUNI_{MES}"].sum().iloc[0] == pytest.approx(1.0, rel=1e-9)

    def test_pondepmuni_proporcional_a_produccion_dpto(self):
        df = _df(
            _fila(muni="Belmira",  cod_muni="05086", idfinca="A", prod=300.0),
            _fila(muni="Medellin", cod_muni="05001", idfinca="B", prod=700.0),
        )
        out = calc(df).sort_values("MUNICIPIO").reset_index(drop=True)
        assert out.iloc[0][f"PONDEPMUNI_{MES}"] == pytest.approx(0.30, rel=1e-6)
        assert out.iloc[1][f"PONDEPMUNI_{MES}"] == pytest.approx(0.70, rel=1e-6)

    def test_pondepmuni_independiente_entre_dptos(self):
        """Municipios de distintos dptos tienen PONDEPMUNI independiente."""
        df = _df(
            _fila(dept="Antioquia", muni="Belmira", cod_dep="05", cod_muni="05086", prod=500.0),
            _fila(dept="Boyaca",    muni="Tunja",   cod_dep="15", cod_muni="15001", prod=1000.0),
        )
        out = calc(df)
        # Cada dpto tiene un solo muni → PONDEPMUNI = 1 para ambos
        np.testing.assert_allclose(
            out[f"PONDEPMUNI_{MES}"].values, np.ones(len(out)), atol=1e-9
        )


# ─── Act 35: Columnas sufijadas ───────────────────────────────────────────────

class TestColumnasSufijadas:
    def test_columnas_fijas(self):
        out = calc(_df(_fila()))
        for col in ["DEPARTAMENTO", "MUNICIPIO", "COD_DEP", "COD_MUNI", "IDDEPMUNI"]:
            assert col in out.columns

    def test_columnas_dinamicas(self):
        out = calc(_df(_fila()))
        for col in [f"MINPRECIO_MUNI_{MES}", f"MAXPRECIO_MUNI_{MES}",
                    f"ME_PRECIO_MUNI_{MES}", f"SD_PRECIO_MUNI_{MES}",
                    f"T_VACAS_MUNI_{MES}", f"ME_PRODUCCION_MUNI_{MES}",
                    f"T_PRODUCCION_MUNI_{MES}", f"SD_PRODUCCION_MUNI_{MES}",
                    f"T_VENTA_MUNI_{MES}", f"PON_NACIONAL_{MES}",
                    f"PRODDEP_{MES}", f"PONDEPMUNI_{MES}"]:
            assert col in out.columns, f"Columna {col} faltante"

    def test_iddepmuni_sin_espacios(self):
        df = _df(_fila(dept="Valle Del Cauca", muni="Santiago De Cali",
                       cod_dep="76", cod_muni="76001"))
        out = calc(df)
        assert " " not in out.iloc[0]["IDDEPMUNI"]
        assert out.iloc[0]["IDDEPMUNI"] == "ValleDelCaucaSantiagoDeCali"

    def test_cod_muni_5_digitos(self):
        out = calc(_df(_fila()))
        assert out["COD_MUNI"].str.match(r"^\d{5}$").all()


# ─── Act 36: Regresión numérica vs referencia SAS ────────────────────────────

RUTA_REF = (
    r"C:\Users\Jeferson\OneDrive - Cloud Integration Hub"
    r"\Documentos\DANE Automatización\SIPSA Leche"
    r"\CUADROS_032026_TOT.xls.xlsx"
)
RUTA_CLEAN = "data/02_intermediate/BASE_032026_clean.parquet"
TOL_REL = 1e-4  # 0.01% — tolerancia del cronograma Act 36


@pytest.mark.regression
class TestRegressionVsReferenciaSAS:
    """Compara ME_PRECIO_MUNI_MAR, SD_PRECIO_MUNI_MAR y PON_NACIONAL_MAR
    contra la hoja MUNICIPIO de CUADROS_032026_TOT.xls."""

    @pytest.fixture(scope="class")
    def ref_muni(self):
        import os
        if not os.path.exists(RUTA_REF):
            pytest.skip("Referencia SAS no disponible")
        ref = pd.read_excel(RUTA_REF, sheet_name="MUNICIPIO", dtype=str)
        for col in ["ME_PRECIO_MUNI_MAR", "SD_PRECIO_MUNI_MAR", "PON_NACIONAL_MAR",
                    "T_PRODUCCION_MUNI_MAR", "PONDEPMUNI_MAR"]:
            ref[col] = pd.to_numeric(ref[col], errors="coerce")
        return ref

    @pytest.fixture(scope="class")
    def resultado(self):
        import os
        if not os.path.exists(RUTA_CLEAN):
            pytest.skip("BASE_032026_clean.parquet no disponible")
        base = pd.read_parquet(RUTA_CLEAN)
        return calcular_precio_municipio(base, "MAR")

    def test_numero_municipios_igual(self, ref_muni, resultado):
        assert len(resultado) == len(ref_muni), (
            f"Municipios: Python={len(resultado)}, Referencia={len(ref_muni)}"
        )

    def test_me_precio_muni_dentro_tolerancia(self, ref_muni, resultado):
        merged = resultado.merge(
            ref_muni[["IDDEPMUNI", "ME_PRECIO_MUNI_MAR"]].rename(
                columns={"ME_PRECIO_MUNI_MAR": "REF"}),
            on="IDDEPMUNI", how="inner"
        )
        diff_rel = (
            (merged["ME_PRECIO_MUNI_MAR"] - merged["REF"]).abs()
            / merged["REF"].replace(0, np.nan)
        ).dropna()
        pct_fuera = (diff_rel > TOL_REL).mean() * 100
        assert pct_fuera == 0.0, (
            f"{pct_fuera:.2f}% de municipios fuera de tolerancia. "
            f"Max diff: {diff_rel.max():.2e}"
        )

    def test_sd_precio_muni_dentro_tolerancia(self, ref_muni, resultado):
        merged = resultado.merge(
            ref_muni[["IDDEPMUNI", "SD_PRECIO_MUNI_MAR"]].rename(
                columns={"SD_PRECIO_MUNI_MAR": "REF"}),
            on="IDDEPMUNI", how="inner"
        )
        # Para SD=0 (precio constante en el municipio), tolerancia absoluta
        nonzero = merged["REF"] > 1e-6
        if nonzero.any():
            diff_rel = ((merged.loc[nonzero, "SD_PRECIO_MUNI_MAR"] -
                         merged.loc[nonzero, "REF"]).abs() /
                        merged.loc[nonzero, "REF"]).max()
            assert diff_rel < TOL_REL, f"SD_PRECIO max diff rel: {diff_rel:.2e}"

    def test_t_produccion_muni_exacta(self, ref_muni, resultado):
        merged = resultado.merge(
            ref_muni[["IDDEPMUNI", "T_PRODUCCION_MUNI_MAR"]].rename(
                columns={"T_PRODUCCION_MUNI_MAR": "REF"}),
            on="IDDEPMUNI", how="inner"
        )
        np.testing.assert_allclose(
            merged["T_PRODUCCION_MUNI_MAR"].values,
            merged["REF"].values,
            rtol=1e-9,
            err_msg="T_PRODUCCION_MUNI_MAR difiere de la referencia",
        )

    def test_pon_nacional_suma_1(self, resultado):
        total = resultado[f"PON_NACIONAL_{MES}"].sum()
        assert abs(total - 1.0) < 1e-9, f"PON_NACIONAL no suma 1: {total}"

    def test_pondepmuni_suma_1_por_dpto(self, resultado):
        sumas = resultado.groupby("DEPARTAMENTO")[f"PONDEPMUNI_{MES}"].sum()
        np.testing.assert_allclose(
            sumas.values,
            np.ones(len(sumas)),
            atol=1e-9,
            err_msg="PONDEPMUNI_MAR no suma 1 en algún departamento",
        )
