"""Tests del pipeline cleaning — M2 Act 14: Depuración de la Encuesta de Leche Cruda.

Cubre los 9 pasos de transformación y los casos especiales del cronograma:
  Act 6  — Cast numérico
  Act 7  — PROPCASE / UPCASE
  Act 8  — Formato Z7 de IDFINCA
  Act 9  — Corrección JAMUNDÍ
  Act 10 — 14 correcciones de IDFINCA (incluye notación científica 07.69E7)
  Act 11 — Extracción COD_DEP y COD_MUNI
  Act 12 — Regla vacas en ordeño
  Act 13 — Regla venta de leche
"""
from __future__ import annotations

import pandas as pd
import pytest

from sipsa_leche.pipelines.cleaning.nodes import depurar_base

# ─── Fixtures de parámetros (espejo de parameters.yml) ───────────────────────

CORRECTIONS = [
    {"wrong": "0508301", "municipio": "Belmira",              "correct": "0508601"},
    {"wrong": "0515402", "municipio": "El Carmen De Viboral", "correct": "0514802"},
    {"wrong": "0086312", "municipio": "Sabanalarga",          "correct": "0863812"},
    {"wrong": "1756319", "municipio": "Salamina",             "correct": "1765319"},
    {"wrong": "1756312", "municipio": "Salamina",             "correct": "1765312"},
    {"wrong": "2562905", "municipio": "Facatativa",           "correct": "2526905"},
    {"wrong": "6919018", "municipio": "Cimitarra",            "correct": "6819018"},
    {"wrong": "07.69E7", "municipio": "Zarzal",               "correct": "7689510"},
    {"wrong": "76895010","municipio": "Zarzal",               "correct": "7689510"},
    {"wrong": "76895011","municipio": "Zarzal",               "correct": "7689511"},
    {"wrong": "7636510", "municipio": "Jamundí",              "correct": "7636410"},
    {"wrong": "0475515", "municipio": "Plato",                "correct": "4755515"},
    {"wrong": "0475516", "municipio": "Plato",                "correct": "4755516"},
    {"wrong": "0475517", "municipio": "Plato",                "correct": "4755517"},
]

MACROREGIONES = {
    "CAUCA,NARIÑO Y VALLE DEL CAUCA ": ["19", "52", "76", "86"],
    "ZONA CAFETERA":                    ["05", "17", "63", "66"],
    "BOYACA Y CUNDINAMARCA":            ["15", "25"],
    "COSTA ATLANTICA":                  ["08", "13", "20", "23", "44", "47", "70"],
    "RESTO":                            ["85", "41", "50", "54", "68", "73", "18", "81"],
}


# ─── Helper ───────────────────────────────────────────────────────────────────

def _raw(**overrides) -> pd.DataFrame:
    """Finca de referencia en formato raw (strings, como sale del Excel)."""
    row = {
        "IDFINCA":      "0508601",    # Belmira — ya correcto, COD_DEP=05 → ZONA CAFETERA
        "MUNICIPIO":    "BELMIRA",
        "DEPARTAMENTO": "ANTIOQUIA",
        "FINCA":        "LA ESPERANZA",
        "VACASOR":      "5",
        "PRECIOLITROS": "1200",
        "PRODUCCION":   "100",
        "VENTA":        "80",
        "MES":          "marzo",
    }
    row.update(overrides)
    return pd.DataFrame([row])


def clean(df: pd.DataFrame) -> pd.DataFrame:
    return depurar_base(df, CORRECTIONS, MACROREGIONES)


# ─── Act 6: Cast numérico ─────────────────────────────────────────────────────

class TestCastNumerico:
    def test_columnas_son_float(self):
        df = clean(_raw())
        for col in ["VACASOR", "PRECIOLITROS", "PRODUCCION", "VENTA"]:
            assert df[col].dtype == float, f"{col} debe ser float"

    def test_texto_no_numerico_queda_nan(self):
        df = clean(_raw(VACASOR="5", PRECIOLITROS="N/D", PRODUCCION="100", VENTA="80"))
        assert pd.isna(df.iloc[0]["PRECIOLITROS"])

    def test_valores_numericos_correctos(self):
        df = clean(_raw(VACASOR="8", PRECIOLITROS="1500", PRODUCCION="200", VENTA="150"))
        row = df.iloc[0]
        assert row["VACASOR"] == 8.0
        assert row["PRECIOLITROS"] == 1500.0
        assert row["PRODUCCION"] == 200.0
        assert row["VENTA"] == 150.0


# ─── Act 7: Normalización de texto ───────────────────────────────────────────

class TestNormalizacionTexto:
    def test_municipio_propcase(self):
        df = clean(_raw(MUNICIPIO="MEDELLIN"))
        assert df.iloc[0]["MUNICIPIO"] == "Medellin"

    def test_departamento_propcase(self):
        df = clean(_raw())
        assert df.iloc[0]["DEPARTAMENTO"] == "Antioquia"

    def test_finca_propcase(self):
        df = clean(_raw())
        assert df.iloc[0]["FINCA"] == "La Esperanza"

    def test_mes_upcase(self):
        df = clean(_raw(MES="marzo"))
        assert df.iloc[0]["MES"] == "MARZO"

    def test_mes_ya_mayusculas(self):
        df = clean(_raw(MES="MARZO"))
        assert df.iloc[0]["MES"] == "MARZO"

    def test_espacios_extremos_eliminados(self):
        df = clean(_raw(MUNICIPIO="  BELMIRA  "))
        assert df.iloc[0]["MUNICIPIO"] == "Belmira"


# ─── Act 8: Formato Z7 de IDFINCA ────────────────────────────────────────────

class TestFormatoIdfinca:
    def test_idfinca_6_digitos_padded_a_7(self):
        df = clean(_raw(IDFINCA="508601"))
        assert df.iloc[0]["IDFINCA"] == "0508601"

    def test_idfinca_ya_7_digitos_sin_cambio(self):
        df = clean(_raw(IDFINCA="0508601"))
        assert df.iloc[0]["IDFINCA"] == "0508601"

    def test_idfinca_5_digitos_padded(self):
        df = clean(_raw(IDFINCA="86381", MUNICIPIO="SABANALARGA", DEPARTAMENTO="ATLANTICO"))
        assert df.iloc[0]["IDFINCA"] == "0086381"


# ─── Act 9: Corrección JAMUNDÍ ────────────────────────────────────────────────

class TestCorreccionJamundi:
    def test_jamundi_sin_acento_corregido(self):
        df = clean(_raw(IDFINCA="7636410", MUNICIPIO="JAMUNDI", DEPARTAMENTO="VALLE DEL CAUCA"))
        assert df.iloc[0]["MUNICIPIO"] == "Jamundí"

    def test_jamundi_con_acento_intacto(self):
        df = clean(_raw(IDFINCA="7636410", MUNICIPIO="JAMUNDÍ", DEPARTAMENTO="VALLE DEL CAUCA"))
        assert df.iloc[0]["MUNICIPIO"] == "Jamundí"

    def test_otros_municipios_no_afectados(self):
        df = clean(_raw(MUNICIPIO="BOGOTA", DEPARTAMENTO="CUNDINAMARCA", IDFINCA="2500001"))
        assert df.iloc[0]["MUNICIPIO"] == "Bogota"


# ─── Act 10: 14 correcciones de IDFINCA ──────────────────────────────────────

@pytest.mark.parametrize("wrong, municipio_raw, correct", [
    ("0508301", "BELMIRA",              "0508601"),
    ("0515402", "EL CARMEN DE VIBORAL", "0514802"),
    ("0086312", "SABANALARGA",          "0863812"),
    ("1756319", "SALAMINA",             "1765319"),
    ("1756312", "SALAMINA",             "1765312"),
    ("2562905", "FACATATIVA",           "2526905"),
    ("6919018", "CIMITARRA",            "6819018"),
    ("76895010","ZARZAL",               "7689510"),
    ("76895011","ZARZAL",               "7689511"),
    ("7636510", "JAMUNDI",              "7636410"),
    ("0475515", "PLATO",                "4755515"),
    ("0475516", "PLATO",                "4755516"),
    ("0475517", "PLATO",                "4755517"),
])
def test_correccion_idfinca(wrong: str, municipio_raw: str, correct: str):
    df = clean(_raw(IDFINCA=wrong, MUNICIPIO=municipio_raw, DEPARTAMENTO="COLOMBIA"))
    assert df.iloc[0]["IDFINCA"] == correct, (
        f"IDFINCA '{wrong}' en {municipio_raw} debería corregirse a '{correct}'"
    )


def test_correccion_idfinca_notacion_cientifica():
    """07.69E7 (notación científica generada por Excel) → '7689510'.

    Caso especial documentado en el cronograma Act 10:
    Excel convierte 7689510 a '07.69E7' cuando la celda tiene formato número.
    """
    df = clean(_raw(IDFINCA="07.69E7", MUNICIPIO="ZARZAL", DEPARTAMENTO="VALLE DEL CAUCA"))
    assert df.iloc[0]["IDFINCA"] == "7689510", (
        "IDFINCA en notación científica '07.69E7' debe convertirse a '7689510'"
    )


def test_idfinca_correcto_no_modificado():
    """IDFINCA correcto en el mismo municipio NO debe alterarse."""
    df = clean(_raw(IDFINCA="0508601", MUNICIPIO="BELMIRA", DEPARTAMENTO="ANTIOQUIA"))
    assert df.iloc[0]["IDFINCA"] == "0508601"


# ─── Act 11: Extracción de códigos geográficos ───────────────────────────────

class TestCodigosGeograficos:
    def test_cod_dep_2_digitos(self):
        df = clean(_raw(IDFINCA="0508601"))
        assert df.iloc[0]["COD_DEP"] == "05"

    def test_cod_muni_5_digitos(self):
        df = clean(_raw(IDFINCA="0508601"))
        assert df.iloc[0]["COD_MUNI"] == "05086"

    def test_cod_dep_regex(self):
        df = clean(_raw())
        assert df["COD_DEP"].str.match(r"^\d{2}$").all()

    def test_cod_muni_regex(self):
        df = clean(_raw())
        assert df["COD_MUNI"].str.match(r"^\d{5}$").all()

    def test_cod_dep_diferente_departamento(self):
        df = clean(_raw(IDFINCA="7636410", MUNICIPIO="JAMUNDÍ", DEPARTAMENTO="VALLE DEL CAUCA"))
        assert df.iloc[0]["COD_DEP"] == "76"
        assert df.iloc[0]["COD_MUNI"] == "76364"


# ─── Asignación de macrorregión ───────────────────────────────────────────────

class TestMacroRegion:
    def test_antioquia_zona_cafetera(self):
        df = clean(_raw(IDFINCA="0508601"))
        assert df.iloc[0]["MACRO"] == "ZONA CAFETERA"

    def test_valle_cauca_nariño(self):
        df = clean(_raw(IDFINCA="7636410", MUNICIPIO="JAMUNDÍ", DEPARTAMENTO="VALLE DEL CAUCA"))
        assert df.iloc[0]["MACRO"] == "CAUCA,NARIÑO Y VALLE DEL CAUCA "

    def test_cundinamarca_boyaca(self):
        df = clean(_raw(IDFINCA="2500001", MUNICIPIO="BOGOTA", DEPARTAMENTO="CUNDINAMARCA"))
        assert df.iloc[0]["MACRO"] == "BOYACA Y CUNDINAMARCA"

    def test_atlantico_costa(self):
        df = clean(_raw(IDFINCA="0800001", MUNICIPIO="BARRANQUILLA", DEPARTAMENTO="ATLANTICO"))
        assert df.iloc[0]["MACRO"] == "COSTA ATLANTICA"


# ─── Act 12: Regla vacas en ordeño ───────────────────────────────────────────

class TestReglaVacas:
    def test_vacasor_nulo_pone_todo_en_cero(self):
        df = clean(_raw(VACASOR=None, PRECIOLITROS="1200", PRODUCCION="100", VENTA="80"))
        row = df.iloc[0]
        assert row["VACASOR"] == 0.0
        assert row["PRECIOLITROS"] == 0.0
        assert row["PRODUCCION"] == 0.0
        assert row["VENTA"] == 0.0

    def test_vacasor_cero_pone_indicadores_en_cero(self):
        df = clean(_raw(VACASOR="0", PRECIOLITROS="1200", PRODUCCION="100", VENTA="80"))
        row = df.iloc[0]
        assert row["PRECIOLITROS"] == 0.0
        assert row["PRODUCCION"] == 0.0
        assert row["VENTA"] == 0.0

    def test_vacasor_positivo_preserva_valores(self):
        df = clean(_raw(VACASOR="10", PRECIOLITROS="1800", PRODUCCION="250", VENTA="200"))
        row = df.iloc[0]
        assert row["VACASOR"] == 10.0
        assert row["PRODUCCION"] == 250.0
        assert row["VENTA"] == 200.0
        assert row["PRECIOLITROS"] == 1800.0

    def test_vacasor_nunca_nulo_en_salida(self):
        df = clean(_raw(VACASOR=None))
        assert not df["VACASOR"].isna().any()


# ─── Act 13: Regla venta de leche ────────────────────────────────────────────

class TestReglaVenta:
    def test_venta_nula_precio_cero(self):
        df = clean(_raw(VACASOR="5", PRECIOLITROS="1200", PRODUCCION="100", VENTA=None))
        row = df.iloc[0]
        assert row["VENTA"] == 0.0
        assert row["PRECIOLITROS"] == 0.0

    def test_venta_cero_precio_cero(self):
        df = clean(_raw(VACASOR="5", PRECIOLITROS="1200", PRODUCCION="100", VENTA="0"))
        assert df.iloc[0]["PRECIOLITROS"] == 0.0

    def test_venta_positiva_precio_preservado(self):
        df = clean(_raw(VACASOR="5", PRECIOLITROS="1200", PRODUCCION="100", VENTA="80"))
        assert df.iloc[0]["PRECIOLITROS"] == 1200.0

    def test_venta_nunca_nulo_en_salida(self):
        df = clean(_raw(VENTA=None))
        assert not df["VENTA"].isna().any()

    def test_produccion_no_afectada_por_regla_venta(self):
        df = clean(_raw(VACASOR="5", PRECIOLITROS="1200", PRODUCCION="100", VENTA=None))
        assert df.iloc[0]["PRODUCCION"] == 100.0


# ─── Schema de salida ─────────────────────────────────────────────────────────

class TestSchemaOutput:
    def test_idfinca_7_digitos(self):
        df = clean(_raw())
        assert df["IDFINCA"].str.match(r"^\d{7}$").all()

    def test_cod_dep_2_digitos(self):
        df = clean(_raw())
        assert df["COD_DEP"].str.match(r"^\d{2}$").all()

    def test_cod_muni_5_digitos(self):
        df = clean(_raw())
        assert df["COD_MUNI"].str.match(r"^\d{5}$").all()

    def test_numericos_no_negativos(self):
        df = clean(_raw())
        for col in ["VACASOR", "PRECIOLITROS", "PRODUCCION", "VENTA"]:
            assert (df[col].dropna() >= 0).all(), f"{col} tiene valores negativos"

    def test_multiple_registros(self):
        rows = pd.concat([_raw(), _raw(MUNICIPIO="MEDELLIN", IDFINCA="0500001")], ignore_index=True)
        df = clean(rows)
        assert len(df) == 2
        assert df["IDFINCA"].str.match(r"^\d{7}$").all()
