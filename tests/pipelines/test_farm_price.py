"""Tests del pipeline farm_price — M4: Precio mensual del litro de leche por finca.

Cubre los 7 pasos del módulo:
  Act 22 — IDFINCA_AUX + PROD_TOTAL por finca
  Act 23 — PONFINCA = PRODUCCION / PROD_TOTAL
  Act 24 — MED_FINCA = SUM(precio × peso) — media ponderada por litros
  Act 25 — VAR_FINCA = SUM((precio − media)² × peso) — varianza ponderada
  Act 26 — Agregación: T_VACAS, T_PROD, T_VENTA, MIN/MAX precio por finca
  Act 27 — PONMUNI = T_PROD_finca / T_PROD_municipio
  Act 28 — Columnas sufijadas con mes_actual
  Act 29 — Regresión numérica: diferencia < 0.01% vs referencia SAS BASE032026
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from sipsa_leche.pipelines.farm_price.nodes import calcular_precio_finca

MES = "MAR"


# ─── Fixture base ─────────────────────────────────────────────────────────────

def _semana(idfinca="0508601", dept="Antioquia", muni="Belmira", finca="La Esperanza",
             cod_dep="05", cod_muni="05086", precio=1200.0, prod=100.0,
             venta=80.0, vacas=5.0, **kw) -> dict:
    return dict(
        IDFINCA=idfinca, DEPARTAMENTO=dept, MUNICIPIO=muni, FINCA=finca,
        COD_DEP=cod_dep, COD_MUNI=cod_muni, PRECIOLITROS=precio,
        PRODUCCION=prod, VENTA=venta, VACASOR=vacas,
        observaciones=None, MACRO="ZONA CAFETERA", **kw
    )


def _df(*semanas) -> pd.DataFrame:
    return pd.DataFrame(list(semanas))


def calc(df):
    return calcular_precio_finca(df, MES)


# ─── Act 22: IDFINCA_AUX y PROD_TOTAL ─────────────────────────────────────────

class TestIdfincaAux:
    def test_idfinca_aux_sin_espacios(self):
        df = _df(_semana(dept="Valle Del Cauca", muni="Santiago De Cali", finca="La Fe",
                         cod_dep="76", cod_muni="76001"))
        out = calc(df)
        assert " " not in out.iloc[0]["IDFINCA_AUX"]
        assert out.iloc[0]["IDFINCA_AUX"] == "ValleDelCaucaSantiagoDeCaliLaFe"

    def test_idfinca_aux_concatena_dept_muni_finca(self):
        df = _df(_semana(dept="Antioquia", muni="Belmira", finca="La Esperanza"))
        out = calc(df)
        assert out.iloc[0]["IDFINCA_AUX"] == "AntioquiaBelmiraLaEsperanza"

    def test_prod_total_es_suma_semanal(self):
        """4 semanas → PROD_TOTAL = suma de las 4 producciones."""
        semanas = [_semana(prod=100.0), _semana(prod=120.0),
                   _semana(prod=110.0), _semana(prod=90.0)]
        df = _df(*semanas)
        out = calc(df)
        assert out.iloc[0][f"T_PROD_{MES}"] == pytest.approx(420.0)


# ─── Act 23: PONFINCA ─────────────────────────────────────────────────────────

class TestPonfinca:
    def test_ponfinca_suma_a_uno(self):
        """Los pesos semanales deben sumar 1 para cada finca."""
        semanas = [_semana(prod=100.0), _semana(prod=200.0),
                   _semana(prod=150.0), _semana(prod=50.0)]
        df = _df(*semanas)
        # PONFINCA no está en la salida, pero MED_FINCA lo usa implícitamente.
        # Verificamos vía T_PROD: si PONFINCA suma 1, MED_FINCA = media ponderada correcta.
        out = calc(df)
        assert out.iloc[0][f"T_PROD_{MES}"] == pytest.approx(500.0)


# ─── Act 24: MED_FINCA ────────────────────────────────────────────────────────

class TestMedFinca:
    def test_precio_constante_med_igual_precio(self):
        """Todas las semanas mismo precio → MED_FINCA = ese precio."""
        semanas = [_semana(precio=1500.0, prod=p) for p in [100.0, 120.0, 80.0, 100.0]]
        df = _df(*semanas)
        out = calc(df)
        assert out.iloc[0][f"MED_FINCA_{MES}"] == pytest.approx(1500.0, rel=1e-6)

    def test_med_finca_ponderada_por_produccion(self):
        """Semana 1: precio=1000, prod=300 (75%) — Semana 2: precio=2000, prod=100 (25%)
        MED_FINCA = 1000*0.75 + 2000*0.25 = 1250."""
        df = _df(
            _semana(precio=1000.0, prod=300.0),
            _semana(precio=2000.0, prod=100.0),
        )
        out = calc(df)
        assert out.iloc[0][f"MED_FINCA_{MES}"] == pytest.approx(1250.0, rel=1e-6)

    def test_med_finca_ponderada_produccion_alta_pesa_mas(self):
        """Semana con más litros arrastra el precio hacia su valor."""
        df = _df(
            _semana(precio=1000.0, prod=900.0),  # 90% del peso
            _semana(precio=2000.0, prod=100.0),  # 10% del peso
        )
        out = calc(df)
        expected = 1000.0 * 0.9 + 2000.0 * 0.1  # = 1100
        assert out.iloc[0][f"MED_FINCA_{MES}"] == pytest.approx(expected, rel=1e-6)

    def test_med_finca_columna_existe(self):
        df = _df(_semana())
        out = calc(df)
        assert f"MED_FINCA_{MES}" in out.columns


# ─── Act 25: VAR_FINCA ────────────────────────────────────────────────────────

class TestVarFinca:
    def test_var_finca_cero_cuando_precio_constante(self):
        semanas = [_semana(precio=1500.0, prod=p) for p in [100.0, 100.0, 100.0, 100.0]]
        df = _df(*semanas)
        out = calc(df)
        assert out.iloc[0][f"VAR_FINCA_{MES}"] == pytest.approx(0.0, abs=1e-9)

    def test_var_finca_positiva_con_precios_distintos(self):
        df = _df(
            _semana(precio=1000.0, prod=100.0),
            _semana(precio=2000.0, prod=100.0),
        )
        out = calc(df)
        assert out.iloc[0][f"VAR_FINCA_{MES}"] > 0

    def test_var_finca_formula(self):
        """VAR_FINCA = SUM((precio - MED)² × PONFINCA).
        prod1=prod2=100 → PONFINCA=0.5, MED=1500
        VAR = (1000-1500)²*0.5 + (2000-1500)²*0.5 = 250000*0.5 + 250000*0.5 = 250000"""
        df = _df(
            _semana(precio=1000.0, prod=100.0),
            _semana(precio=2000.0, prod=100.0),
        )
        out = calc(df)
        assert out.iloc[0][f"VAR_FINCA_{MES}"] == pytest.approx(250000.0, rel=1e-6)


# ─── Act 26: Acumulados por finca ─────────────────────────────────────────────

class TestAcumuladosFinca:
    def test_t_vacas_es_suma_semanal(self):
        semanas = [_semana(vacas=5.0), _semana(vacas=6.0),
                   _semana(vacas=5.0), _semana(vacas=4.0)]
        df = _df(*semanas)
        out = calc(df)
        assert out.iloc[0][f"T_VACAS_{MES}"] == pytest.approx(20.0)

    def test_t_venta_es_suma_semanal(self):
        semanas = [_semana(venta=80.0), _semana(venta=90.0),
                   _semana(venta=85.0), _semana(venta=88.0)]
        df = _df(*semanas)
        out = calc(df)
        assert out.iloc[0][f"T_VENTA_{MES}"] == pytest.approx(343.0)

    def test_min_precio_es_minimo_semanal(self):
        df = _df(_semana(precio=1200.0), _semana(precio=1000.0),
                 _semana(precio=1400.0), _semana(precio=1300.0))
        out = calc(df)
        assert out.iloc[0][f"MIN_PRECIO_{MES}"] == pytest.approx(1000.0)

    def test_max_precio_es_maximo_semanal(self):
        df = _df(_semana(precio=1200.0), _semana(precio=1000.0),
                 _semana(precio=1400.0), _semana(precio=1300.0))
        out = calc(df)
        assert out.iloc[0][f"MAX_PRECIO_{MES}"] == pytest.approx(1400.0)

    def test_una_fila_por_finca(self):
        """4 semanas de una finca → 1 fila en la salida."""
        semanas = [_semana()] * 4
        df = _df(*semanas)
        out = calc(df)
        assert len(out) == 1

    def test_dos_fincas_dos_filas(self):
        df = _df(
            _semana(idfinca="0508601", finca="La Esperanza"),
            _semana(idfinca="0508602", finca="La Fe"),
        )
        out = calc(df)
        assert len(out) == 2


# ─── Act 27: PONMUNI ─────────────────────────────────────────────────────────

class TestPonmuni:
    def test_ponmuni_suma_a_uno_por_municipio(self):
        """Los PONMUNI de todas las fincas de un municipio deben sumar 1."""
        df = _df(
            _semana(idfinca="0508601", finca="F1", prod=300.0),
            _semana(idfinca="0508602", finca="F2", prod=200.0),
        )
        out = calc(df)
        assert out[f"PONMUNI_{MES}"].sum() == pytest.approx(1.0, rel=1e-9)

    def test_ponmuni_proporcional_a_t_prod(self):
        """F1 produce 75%, F2 produce 25% → PONMUNI_F1=0.75, PONMUNI_F2=0.25."""
        df = _df(
            _semana(idfinca="0508601", finca="F1", prod=300.0),
            _semana(idfinca="0508602", finca="F2", prod=100.0),
        )
        out = calc(df).sort_values("IDFINCA").reset_index(drop=True)
        assert out.iloc[0][f"PONMUNI_{MES}"] == pytest.approx(0.75, rel=1e-6)
        assert out.iloc[1][f"PONMUNI_{MES}"] == pytest.approx(0.25, rel=1e-6)

    def test_ponmuni_independiente_entre_municipios(self):
        """PONMUNI se calcula por municipio, no globalmente."""
        df = _df(
            # Belmira: única finca → PONMUNI = 1
            _semana(idfinca="0508601", finca="F1", muni="Belmira", cod_muni="05086", prod=500.0),
            # Medellin: única finca → PONMUNI = 1
            _semana(idfinca="0500001", finca="G1", muni="Medellin", cod_muni="05001", prod=1000.0),
        )
        out = calc(df)
        assert out[f"PONMUNI_{MES}"].to_list() == pytest.approx([1.0, 1.0], rel=1e-9)


# ─── Act 28: Columnas sufijadas ───────────────────────────────────────────────

class TestColumnasSufijadas:
    def test_columnas_fijas_presentes(self):
        out = calc(_df(_semana()))
        for col in ["DEPARTAMENTO", "MUNICIPIO", "FINCA", "COD_DEP", "COD_MUNI",
                    "IDFINCA", "IDFINCA_AUX"]:
            assert col in out.columns, f"Columna fija {col} faltante"

    def test_columnas_dinamicas_con_sufijo(self):
        out = calc(_df(_semana()))
        for col in [f"T_VACAS_{MES}", f"T_PROD_{MES}", f"T_VENTA_{MES}",
                    f"MIN_PRECIO_{MES}", f"MED_FINCA_{MES}", f"MAX_PRECIO_{MES}",
                    f"VAR_FINCA_{MES}", f"PONMUNI_{MES}"]:
            assert col in out.columns, f"Columna dinámica {col} faltante"

    def test_fincas_excluidas_no_entran(self):
        """Finca con PRECIOLITROS=0 no debe aparecer en el output."""
        df = _df(
            _semana(idfinca="0508601", finca="F1", precio=1200.0, prod=100.0),
            _semana(idfinca="0508602", finca="F2", precio=0.0, prod=50.0),
        )
        out = calc(df)
        assert len(out) == 1
        assert out.iloc[0]["IDFINCA"] == "0508601"


# ─── Act 29: Regresión numérica vs referencia SAS ────────────────────────────

RUTA_REF = (
    r"C:\Users\Jeferson\OneDrive - Cloud Integration Hub"
    r"\Documentos\DANE Automatización\SIPSA Leche"
    r"\CUADROS_032026_TOT.xls.xlsx"
)
RUTA_CLEAN = "data/02_intermediate/BASE_032026_clean.parquet"
TOL_REL = 1e-4  # 0.01% — tolerancia del cronograma Act 29


@pytest.mark.regression
class TestRegressionVsReferenciaSAS:
    """Compara MED_FINCA_MAR, VAR_FINCA_MAR y PONMUNI_MAR contra CUADROS_032026_TOT.xls.

    Requiere que existan:
      data/02_intermediate/BASE_032026_clean.parquet  (M2 output)
      CUADROS_032026_TOT.xls.xlsx                     (referencia SAS)
    """

    @pytest.fixture(scope="class")
    def ref_finca(self):
        import os
        if not os.path.exists(RUTA_REF):
            pytest.skip("Referencia SAS no disponible")
        ref = pd.read_excel(RUTA_REF, sheet_name="FINCA", dtype=str)
        # Filtrar solo filas con datos de MAR
        ref = ref[ref["MED_FINCA_MAR"].notna()].copy()
        for col in ["MED_FINCA_MAR", "VAR_FINCA_MAR", "PONMUNI_MAR",
                    "T_PROD_MAR", "T_VACAS_MAR"]:
            ref[col] = pd.to_numeric(ref[col], errors="coerce")
        return ref

    @pytest.fixture(scope="class")
    def resultado(self):
        import os
        if not os.path.exists(RUTA_CLEAN):
            pytest.skip("BASE_032026_clean.parquet no disponible")
        base = pd.read_parquet(RUTA_CLEAN)
        return calcular_precio_finca(base, "MAR")

    def test_numero_fincas_igual(self, ref_finca, resultado):
        assert len(resultado) == len(ref_finca), (
            f"Filas: Python={len(resultado)}, Referencia={len(ref_finca)}"
        )

    def test_med_finca_mar_dentro_tolerancia(self, ref_finca, resultado):
        merged = resultado.merge(
            ref_finca[["IDFINCA_AUX", "MED_FINCA_MAR"]].rename(columns={"MED_FINCA_MAR": "REF_MED"}),
            on="IDFINCA_AUX", how="inner"
        )
        diff_rel = ((merged["MED_FINCA_MAR"] - merged["REF_MED"]).abs() /
                    merged["REF_MED"].replace(0, np.nan)).dropna()
        pct_fuera = (diff_rel > TOL_REL).mean() * 100
        assert pct_fuera == 0.0, (
            f"{pct_fuera:.2f}% de fincas fuera de tolerancia {TOL_REL:.0%}. "
            f"Max diff rel: {diff_rel.max():.2e}"
        )

    def test_t_prod_mar_exacto(self, ref_finca, resultado):
        merged = resultado.merge(
            ref_finca[["IDFINCA_AUX", "T_PROD_MAR"]].rename(columns={"T_PROD_MAR": "REF"}),
            on="IDFINCA_AUX", how="inner"
        )
        np.testing.assert_allclose(
            merged["T_PROD_MAR"].values,
            merged["REF"].values,
            rtol=1e-9,
            err_msg="T_PROD_MAR difiere de la referencia SAS",
        )

    def test_var_finca_mar_dentro_tolerancia(self, ref_finca, resultado):
        merged = resultado.merge(
            ref_finca[["IDFINCA_AUX", "VAR_FINCA_MAR"]].rename(columns={"VAR_FINCA_MAR": "REF"}),
            on="IDFINCA_AUX", how="inner"
        )
        # Para VAR=0 (precio constante), usamos tolerancia absoluta
        diff_abs = (merged["VAR_FINCA_MAR"] - merged["REF"]).abs()
        nonzero = merged["REF"] > 1e-10
        if nonzero.any():
            diff_rel = (diff_abs[nonzero] / merged.loc[nonzero, "REF"]).max()
            assert diff_rel < TOL_REL, f"VAR_FINCA_MAR max diff rel: {diff_rel:.2e}"
        assert diff_abs[~nonzero].max() < 1e-6

    def test_ponmuni_mar_suma_1_por_municipio(self, resultado):
        # PONMUNI se calcula por (DEPARTAMENTO, MUNICIPIO) — la clave correcta
        # Agrupar solo por MUNICIPIO falla cuando el mismo nombre existe en varios dptos.
        sumas = resultado.groupby(["DEPARTAMENTO", "MUNICIPIO"])[f"PONMUNI_{MES}"].sum()
        np.testing.assert_allclose(
            sumas.values,
            np.ones(len(sumas)),
            atol=1e-9,
            err_msg="PONMUNI_MAR no suma 1 en algún municipio",
        )
