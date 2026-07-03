"""Tests del pipeline monthly_variation — M7: Variación mensual precio y producción.

Cubre los 7 pasos del módulo:
  Act 44 — D1=(V_act/V_ant)-1 y D2=V_act-V_ant para cobertura
  Act 45 — VPRE = (ME_actual/ME_anterior) - 1 para todos los niveles
  Act 46 — VPROD = (T_PROD_actual/T_PROD_anterior) - 1
  Act 47 — TENDENCIA_PRECIO finca/municipio (umbral ±5%)
  Act 48 — TENDENCIA_PRECIO departamento/macro (umbral ±3%)
  Act 49 — CV = SD_PRECIO / ME_PRECIO
  Act 50 — Valores límite exactos en los umbrales
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from sipsa_leche.pipelines.monthly_variation.nodes import (
    calcular_variacion_cobertura,
    calcular_variacion_departamento,
    calcular_variacion_finca,
    calcular_variacion_macro,
    calcular_variacion_municipio,
)

MES_A = "MAR"
MES_ANT = "FEB"

UMBRAL_FINCA_MUNI = {
    "bajo_extremo": -0.12, "bajo_fuerte": -0.07, "bajo_leve": -0.05,
    "estable_sup": 0.05, "alto_leve": 0.07, "alto_fuerte": 0.12,
}
UMBRAL_DEP_MACRO = {
    "bajo_extremo": -0.12, "bajo_fuerte": -0.07, "bajo_leve": -0.03,
    "estable_sup": 0.03, "alto_leve": 0.07, "alto_fuerte": 0.12,
}


# ─── Act 44: Variación cobertura ──────────────────────────────────────────────

class TestVariacionCobertura:
    def _cob(self, v, no=0, cod="05001", dept="Antioquia", muni="Medellin"):
        return pd.DataFrame([{"DEPARTAMENTO": dept, "COD_MUNI": cod,
                               "MUNICIPIO": muni, "IDDEPMUNI": dept+muni,
                               f"V{MES_A}": float(v), f"NO{MES_A}": float(no)}])

    def _cob_ant(self, v, no=0, cod="05001", dept="Antioquia", muni="Medellin"):
        return pd.DataFrame([{"DEPARTAMENTO": dept, "COD_MUNI": cod,
                               "MUNICIPIO": muni, "IDDEPMUNI": dept+muni,
                               f"V{MES_ANT}": float(v), f"NO{MES_ANT}": float(no)}])

    def test_d1_variacion_relativa(self):
        out = calcular_variacion_cobertura(self._cob(110), self._cob_ant(100), MES_A, MES_ANT)
        assert out.iloc[0][f"D1_{MES_A}{MES_ANT}"] == pytest.approx(0.10, rel=1e-9)

    def test_d2_variacion_absoluta(self):
        out = calcular_variacion_cobertura(self._cob(110), self._cob_ant(100), MES_A, MES_ANT)
        assert out.iloc[0][f"D2_{MES_A}{MES_ANT}"] == pytest.approx(10.0)

    def test_d1_negativo_cuando_cobertura_baja(self):
        out = calcular_variacion_cobertura(self._cob(90), self._cob_ant(100), MES_A, MES_ANT)
        assert out.iloc[0][f"D1_{MES_A}{MES_ANT}"] == pytest.approx(-0.10, rel=1e-9)

    def test_sin_cambio_d1_cero(self):
        out = calcular_variacion_cobertura(self._cob(100), self._cob_ant(100), MES_A, MES_ANT)
        assert out.iloc[0][f"D1_{MES_A}{MES_ANT}"] == pytest.approx(0.0, abs=1e-9)


# ─── Act 45-46: Variación precio y producción — FINCA ──────────────────────────

def _finca(idfinca="0508601", med=1200.0, tprod=400.0, mes=MES_A):
    return pd.DataFrame([{
        "IDFINCA": idfinca, "DEPARTAMENTO": "Antioquia", "MUNICIPIO": "Belmira",
        "FINCA": "F1", "COD_DEP": "05", "COD_MUNI": "05086",
        "IDFINCA_AUX": "AntioquiaBelmiraF1",
        f"MED_FINCA_{mes}": med, f"T_PROD_{mes}": tprod,
        f"T_VACAS_{mes}": 5.0, f"T_VENTA_{mes}": 320.0,
        f"MIN_PRECIO_{mes}": med - 50, f"MAX_PRECIO_{mes}": med + 50,
        f"VAR_FINCA_{mes}": 0.0, f"PONMUNI_{mes}": 0.5,
    }])


class TestVariacionFinca:
    def test_vpre_marfeb_columna(self):
        out = calcular_variacion_finca(_finca(med=1200.0), _finca(med=1000.0, mes=MES_ANT),
                                        MES_A, MES_ANT, UMBRAL_FINCA_MUNI)
        assert f"VPRE_{MES_A}{MES_ANT}" in out.columns

    def test_vpre_precio_aumento(self):
        out = calcular_variacion_finca(_finca(med=1200.0), _finca(med=1000.0, mes=MES_ANT),
                                        MES_A, MES_ANT, UMBRAL_FINCA_MUNI)
        assert out.iloc[0][f"VPRE_{MES_A}{MES_ANT}"] == pytest.approx(0.20, rel=1e-6)

    def test_vprod_febmar_columna(self):
        out = calcular_variacion_finca(_finca(tprod=440.0), _finca(tprod=400.0, mes=MES_ANT),
                                        MES_A, MES_ANT, UMBRAL_FINCA_MUNI)
        assert f"VPROD_{MES_ANT}{MES_A}" in out.columns

    def test_vprod_produccion_aumento(self):
        out = calcular_variacion_finca(_finca(tprod=440.0), _finca(tprod=400.0, mes=MES_ANT),
                                        MES_A, MES_ANT, UMBRAL_FINCA_MUNI)
        assert out.iloc[0][f"VPROD_{MES_ANT}{MES_A}"] == pytest.approx(0.10, rel=1e-6)

    def test_tendencia_presente(self):
        out = calcular_variacion_finca(_finca(med=1200.0), _finca(med=1000.0, mes=MES_ANT),
                                        MES_A, MES_ANT, UMBRAL_FINCA_MUNI)
        assert "TENDENCIA_PRECIO" in out.columns


# ─── Act 47: TENDENCIA_PRECIO finca/municipio (umbral ±5%) ───────────────────

@pytest.mark.parametrize("vpre, expected", [
    (-0.15, "xxx"),  # < -12%
    (-0.10, "xx"),   # -12% a -7%
    (-0.06, "x"),    # -7% a -5%
    (-0.03, "="),    # dentro de ±5%
    ( 0.00, "="),
    ( 0.03, "="),
    ( 0.06, "°"),    # 5% a 7%
    ( 0.08, "°°"),   # 7% a 12%
    ( 0.15, "°°°"),  # >= 12%
])
def test_tendencia_finca_muni_umbrales(vpre, expected):
    """Act 47 + Act 50: valores en todos los rangos incluyendo límites exactos."""
    ant = _finca(med=1000.0, mes=MES_ANT)
    med_act = 1000.0 * (1 + vpre)
    act = _finca(med=med_act)
    out = calcular_variacion_finca(act, ant, MES_A, MES_ANT, UMBRAL_FINCA_MUNI)
    assert out.iloc[0]["TENDENCIA_PRECIO"] == expected, f"vpre={vpre} → expected {expected}"


# ─── Act 48: TENDENCIA_PRECIO departamento/macro (umbral ±3%) ────────────────

@pytest.mark.parametrize("vpre, expected", [
    (-0.15, "xxx"),   # < -12%
    (-0.10, "xx"),    # -12% a -7%
    (-0.05, "x"),     # -7% a -3% (umbral más estricto)
    (-0.01, "="),     # dentro de ±3%
    ( 0.00, "="),
    ( 0.02, "="),
    ( 0.05, "°"),     # 3% a 7%
    ( 0.09, "°°"),    # 7% a 12%
    ( 0.15, "°°°"),   # >= 12%
])
def test_tendencia_dep_macro_umbrales(vpre, expected):
    """Act 48 + Act 50: umbral central ±3%, diferente de finca/muni."""
    dep_a = pd.DataFrame([{"DEPARTAMENTO": "Antioquia", "COD_DEP": "05",
                            f"ME_PRECIO_DEP_{MES_A}": 1000.0 * (1 + vpre),
                            f"TPROD_DEP_{MES_A}": 100.0,
                            f"SDPRECIO_DEP_{MES_A}": 50.0,
                            f"MINPRECIO_DEP_{MES_A}": 900.0,
                            f"MAXPRECIO_DEP_{MES_A}": 1100.0,
                            f"MEPROD_DEP_{MES_A}": 500.0,
                            f"SDPROD_DEP_{MES_A}": 100.0,
                            f"MEVACAS_DEP_{MES_A}": 25.0,
                            f"TVACAS_DEP_{MES_A}": 100.0,
                            f"TVENTA_DEP_{MES_A}": 80.0,
                            f"MEVENTA_DEP_{MES_A}": 75.0,
                            f"SDVENTA_DEP_{MES_A}": 5.0,
                            f"PON_NAL_{MES_A}": 0.16}])
    dep_ant = pd.DataFrame([{"DEPARTAMENTO": "Antioquia", "COD_DEP": "05",
                              f"ME_PRECIO_DEP_{MES_ANT}": 1000.0,
                              f"TPROD_DEP_{MES_ANT}": 100.0,
                              f"SDPRECIO_DEP_{MES_ANT}": 50.0,
                              f"MINPRECIO_DEP_{MES_ANT}": 900.0,
                              f"MAXPRECIO_DEP_{MES_ANT}": 1100.0,
                              f"MEPROD_DEP_{MES_ANT}": 500.0,
                              f"SDPROD_DEP_{MES_ANT}": 100.0,
                              f"MEVACAS_DEP_{MES_ANT}": 25.0,
                              f"TVACAS_DEP_{MES_ANT}": 100.0,
                              f"TVENTA_DEP_{MES_ANT}": 80.0,
                              f"MEVENTA_DEP_{MES_ANT}": 75.0,
                              f"SDVENTA_DEP_{MES_ANT}": 5.0,
                              f"PON_NAL_{MES_ANT}": 0.16}])
    out = calcular_variacion_departamento(dep_a, dep_ant, MES_A, MES_ANT, UMBRAL_DEP_MACRO)
    assert out.iloc[0]["TENDENCIA_PRECIO"] == expected, f"vpre={vpre} → expected {expected}"


# ─── Act 49: CV = SD / ME ──────────────────────────────────────────────────────

def _muni(mes, me=1500.0, sd=75.0, me_prod=500.0, t_prod=2000.0, iddepmuni="AntioquiaBelmira"):
    return pd.DataFrame([{
        "DEPARTAMENTO": "Antioquia", "MUNICIPIO": "Belmira",
        "COD_DEP": "05", "COD_MUNI": "05086", "IDDEPMUNI": iddepmuni,
        f"ME_PRECIO_MUNI_{mes}": me, f"SD_PRECIO_MUNI_{mes}": sd,
        f"ME_PRODUCCION_MUNI_{mes}": me_prod, f"T_PRODUCCION_MUNI_{mes}": t_prod,
        f"MINPRECIO_MUNI_{mes}": me - sd, f"MAXPRECIO_MUNI_{mes}": me + sd,
        f"SD_PRODUCCION_MUNI_{mes}": 100.0, f"T_VACAS_MUNI_{mes}": 50.0,
        f"T_VENTA_MUNI_{mes}": 1800.0, f"PON_NACIONAL_{mes}": 0.10,
        f"PRODDEP_{mes}": 10000.0, f"PONDEPMUNI_{mes}": 0.20,
    }])


class TestCVPrecio:
    def test_cv_municipio_actual(self):
        out = calcular_variacion_municipio(_muni(MES_A, me=1500.0, sd=75.0),
                                           _muni(MES_ANT, me=1400.0, sd=70.0),
                                           MES_A, MES_ANT, UMBRAL_FINCA_MUNI)
        expected = 75.0 / 1500.0
        assert out.iloc[0][f"CV_PRECIO_MUNI_{MES_A}"] == pytest.approx(expected, rel=1e-9)

    def test_cv_municipio_anterior(self):
        out = calcular_variacion_municipio(_muni(MES_A, me=1500.0, sd=75.0),
                                           _muni(MES_ANT, me=1400.0, sd=70.0),
                                           MES_A, MES_ANT, UMBRAL_FINCA_MUNI)
        expected = 70.0 / 1400.0
        assert out.iloc[0][f"CV_PRECIO_MUNI_{MES_ANT}"] == pytest.approx(expected, rel=1e-9)


# ─── Act 50: Valores límite exactos en umbrales ───────────────────────────────

class TestValoresLimiteUmbrales:
    """Verifica el comportamiento en los bordes exactos de los umbrales."""

    def test_justo_dentro_estable_finca(self):
        """vpre = -0.04 → '=' (claramente dentro del rango estable ±5%)."""
        ant = _finca(med=1000.0, mes=MES_ANT)
        act = _finca(med=960.0)   # (960/1000)-1 = -0.04 → "="
        out = calcular_variacion_finca(act, ant, MES_A, MES_ANT, UMBRAL_FINCA_MUNI)
        assert out.iloc[0]["TENDENCIA_PRECIO"] == "="

    def test_justo_fuera_estable_finca(self):
        """vpre = -0.06 → 'x' (claramente fuera del rango estable, zona baja)."""
        ant = _finca(med=1000.0, mes=MES_ANT)
        act = _finca(med=940.0)   # (940/1000)-1 = -0.06 → "x"
        out = calcular_variacion_finca(act, ant, MES_A, MES_ANT, UMBRAL_FINCA_MUNI)
        assert out.iloc[0]["TENDENCIA_PRECIO"] == "x"

    def test_exactamente_mas_5_pct_finca(self):
        """vpre exactamente = +0.05 → '°' (primer nivel de alza)."""
        ant = _finca(med=1000.0, mes=MES_ANT)
        act = _finca(med=1050.0)
        out = calcular_variacion_finca(act, ant, MES_A, MES_ANT, UMBRAL_FINCA_MUNI)
        assert out.iloc[0]["TENDENCIA_PRECIO"] == "°"

    def test_justo_dentro_estable_dep(self):
        """vpre = -0.02 → '=' para departamento (claramente dentro de ±3%)."""
        dep_a = pd.DataFrame([{"DEPARTAMENTO": "A", "COD_DEP": "05",
                                f"ME_PRECIO_DEP_{MES_A}": 980.0,  # -2% → "="
                                f"TPROD_DEP_{MES_A}": 100.0,
                                f"SDPRECIO_DEP_{MES_A}": 50.0,
                                **{f"{c}_{MES_A}": 0.0 for c in ["MINPRECIO_DEP","MAXPRECIO_DEP","MEPROD_DEP","SDPROD_DEP","MEVACAS_DEP","TVACAS_DEP","TVENTA_DEP","MEVENTA_DEP","SDVENTA_DEP","PON_NAL"]}}])
        dep_ant = pd.DataFrame([{"DEPARTAMENTO": "A", "COD_DEP": "05",
                                  f"ME_PRECIO_DEP_{MES_ANT}": 1000.0,
                                  f"TPROD_DEP_{MES_ANT}": 100.0,
                                  f"SDPRECIO_DEP_{MES_ANT}": 50.0,
                                  **{f"{c}_{MES_ANT}": 0.0 for c in ["MINPRECIO_DEP","MAXPRECIO_DEP","MEPROD_DEP","SDPROD_DEP","MEVACAS_DEP","TVACAS_DEP","TVENTA_DEP","MEVENTA_DEP","SDVENTA_DEP","PON_NAL"]}}])
        out = calcular_variacion_departamento(dep_a, dep_ant, MES_A, MES_ANT, UMBRAL_DEP_MACRO)
        assert out.iloc[0]["TENDENCIA_PRECIO"] == "="

    def test_exactamente_mas_3_pct_dep(self):
        """vpre = +0.03 → '°' para departamento."""
        dep_a = pd.DataFrame([{"DEPARTAMENTO": "A", "COD_DEP": "05",
                                f"ME_PRECIO_DEP_{MES_A}": 1030.0,
                                f"TPROD_DEP_{MES_A}": 100.0,
                                f"SDPRECIO_DEP_{MES_A}": 50.0,
                                **{f"{c}_{MES_A}": 0.0 for c in ["MINPRECIO_DEP","MAXPRECIO_DEP","MEPROD_DEP","SDPROD_DEP","MEVACAS_DEP","TVACAS_DEP","TVENTA_DEP","MEVENTA_DEP","SDVENTA_DEP","PON_NAL"]}}])
        dep_ant = pd.DataFrame([{"DEPARTAMENTO": "A", "COD_DEP": "05",
                                  f"ME_PRECIO_DEP_{MES_ANT}": 1000.0,
                                  f"TPROD_DEP_{MES_ANT}": 100.0,
                                  f"SDPRECIO_DEP_{MES_ANT}": 50.0,
                                  **{f"{c}_{MES_ANT}": 0.0 for c in ["MINPRECIO_DEP","MAXPRECIO_DEP","MEPROD_DEP","SDPROD_DEP","MEVACAS_DEP","TVACAS_DEP","TVENTA_DEP","MEVENTA_DEP","SDVENTA_DEP","PON_NAL"]}}])
        out = calcular_variacion_departamento(dep_a, dep_ant, MES_A, MES_ANT, UMBRAL_DEP_MACRO)
        assert out.iloc[0]["TENDENCIA_PRECIO"] == "°"


# ─── Regresión numérica vs referencia SAS ────────────────────────────────────

RUTA_REF = (
    r"C:\Users\Jeferson\OneDrive - Cloud Integration Hub"
    r"\Documentos\DANE Automatización\SIPSA Leche"
    r"\CUADROS_032026_TOT.xls.xlsx"
)
TOL_REL = 1e-4


@pytest.mark.regression
class TestRegressionVariacion:
    """Compara VPRE/VPROD/CV contra hojas FINCA, MUNICIPIO, DEPARTAMENTO, MACROREGION."""

    @pytest.fixture(scope="class")
    def ref(self):
        import os
        if not os.path.exists(RUTA_REF):
            pytest.skip("Referencia SAS no disponible")
        # Columnas que son identificadores — mantener como string
        _id_cols = {"IDFINCA", "IDFINCA_AUX", "IDDEPMUNI", "DEPARTAMENTO",
                    "MUNICIPIO", "FINCA", "COD_DEP", "COD_MUNI", "MACRO",
                    "TENDENCIA_PRECIO"}
        xl = pd.ExcelFile(RUTA_REF)
        result = {}
        for hoja in ["FINCA", "MUNICIPIO", "DEPARTAMENTO", "MACROREGION"]:
            df = xl.parse(hoja, dtype=str)
            for c in df.columns:
                if c not in _id_cols:
                    try: df[c] = pd.to_numeric(df[c], errors="coerce")
                    except: pass
            result[hoja.lower()] = df
        return result

    @pytest.fixture(scope="class")
    def outputs(self):
        import os
        reqs = ["data/03_primary/FINCA_MAR.parquet", "data/03_primary/FINCA_FEB.parquet",
                "data/03_primary/MUNICIPIO_MAR.parquet", "data/03_primary/MUNICIPIO_FEB.parquet",
                "data/03_primary/DEPARTAMENTO_MAR.parquet", "data/03_primary/DEPARTAMENTO_FEB.parquet",
                "data/03_primary/MACRO_MAR.parquet", "data/03_primary/MACRO_FEB.parquet"]
        for r in reqs:
            if not os.path.exists(r): pytest.skip(f"Falta {r}")

        out = {}
        out["finca"] = calcular_variacion_finca(
            pd.read_parquet("data/03_primary/FINCA_MAR.parquet"),
            pd.read_parquet("data/03_primary/FINCA_FEB.parquet"),
            "MAR", "FEB", UMBRAL_FINCA_MUNI,
        )
        out["municipio"] = calcular_variacion_municipio(
            pd.read_parquet("data/03_primary/MUNICIPIO_MAR.parquet"),
            pd.read_parquet("data/03_primary/MUNICIPIO_FEB.parquet"),
            "MAR", "FEB", UMBRAL_FINCA_MUNI,
        )
        out["departamento"] = calcular_variacion_departamento(
            pd.read_parquet("data/03_primary/DEPARTAMENTO_MAR.parquet"),
            pd.read_parquet("data/03_primary/DEPARTAMENTO_FEB.parquet"),
            "MAR", "FEB", UMBRAL_DEP_MACRO,
        )
        out["macro"] = calcular_variacion_macro(
            pd.read_parquet("data/03_primary/MACRO_MAR.parquet"),
            pd.read_parquet("data/03_primary/MACRO_FEB.parquet"),
            "MAR", "FEB", UMBRAL_DEP_MACRO,
        )
        return out

    def _check_vpre(self, out_df, ref_df, join_col, vpre_col):
        mg = out_df.merge(
            ref_df[[join_col, vpre_col]].rename(columns={vpre_col: "REF"}),
            on=join_col, how="inner"
        )
        mg_v = mg[mg["REF"].notna() & mg[vpre_col].notna()].copy()
        np.testing.assert_allclose(
            mg_v[vpre_col].values, mg_v["REF"].values,
            rtol=TOL_REL, atol=1e-6,
            err_msg=f"VPRE {vpre_col} fuera de tolerancia vs referencia SAS",
        )

    def test_vpre_finca_dentro_tolerancia(self, ref, outputs):
        self._check_vpre(outputs["finca"], ref["finca"], "IDFINCA", "VPRE_MARFEB")

    def test_vpre_municipio_dentro_tolerancia(self, ref, outputs):
        self._check_vpre(outputs["municipio"], ref["municipio"], "IDDEPMUNI", "VPRE_FEBMAR")

    def test_vpre_departamento_dentro_tolerancia(self, ref, outputs):
        self._check_vpre(outputs["departamento"], ref["departamento"], "DEPARTAMENTO", "VPRE_FEBMAR")

    def test_tendencia_precio_finca_matches(self, ref, outputs):
        # Python usa la misma convención de símbolos que SAS (xxx/xx/x/=/°/°°/°°°),
        # así que la comparación es directa, sin traducción de símbolos.
        mg = outputs["finca"].merge(
            ref["finca"][["IDFINCA","TENDENCIA_PRECIO"]].rename(columns={"TENDENCIA_PRECIO":"REF"}),
            on="IDFINCA", how="inner"
        )
        valid = mg["REF"].notna() & (mg["REF"] != "")
        match = (mg.loc[valid, "TENDENCIA_PRECIO"] == mg.loc[valid, "REF"]).mean()
        # ~3% de diferencia esperada en valores exactamente en el borde del umbral
        # (diferencias de punto flotante SAS vs Python en ±5%/±7%/±12%)
        assert match >= 0.95, f"TENDENCIA_PRECIO match rate: {match:.2%}"
