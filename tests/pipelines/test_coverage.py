"""Tests del pipeline coverage — M3 Act 21: Cobertura y fincas excluidas.

Cubre los 6 pasos del módulo:
  Act 16 — Identificación de fincas excluidas (precio=0 o producción=0)
  Act 17 — Construcción de SALEN{PERI} con una fila por finca excluida
  Act 18 — Exportación Excel (relé de datos)
  Act 19 — Conteo de fincas válidas (V{MES}) y excluidas (NO{MES})
  Act 20 — COB_{MES}: merge por IDDEPMUNI
  Act 21 — Invariante: V{MES} + NO{MES} = total fincas del municipio
"""
from __future__ import annotations

import pandas as pd
import pytest

from sipsa_leche.pipelines.coverage.nodes import (
    calcular_cobertura,
    exportar_excluidas_xlsx,
)

MES = "MAR"

# ─── Fixture base ─────────────────────────────────────────────────────────────

def _base(**overrides) -> pd.DataFrame:
    """DataFrame mínimo en formato base_peri_clean (post-M2)."""
    row = {
        "IDFINCA":      "0508601",
        "DEPARTAMENTO": "Antioquia",
        "MUNICIPIO":    "Belmira",
        "FINCA":        "La Esperanza",
        "COD_DEP":      "05",
        "COD_MUNI":     "05086",
        "MACRO":        "ZONA CAFETERA",
        "VACASOR":      5.0,
        "PRECIOLITROS": 1200.0,
        "PRODUCCION":   100.0,
        "VENTA":        80.0,
        "observaciones": None,
    }
    row.update(overrides)
    return pd.DataFrame([row])


def clean(df):
    salen, cob = calcular_cobertura(df, MES)
    return salen, cob


# ─── Act 16: Identificación de excluidas ──────────────────────────────────────

class TestIdentificacionExcluidas:
    def test_precio_cero_excluida(self):
        df = _base(PRECIOLITROS=0.0)
        salen, cob = clean(df)
        assert len(salen) == 1

    def test_produccion_cero_excluida(self):
        df = _base(PRODUCCION=0.0)
        salen, cob = clean(df)
        assert len(salen) == 1

    def test_precio_nulo_excluida(self):
        df = _base(PRECIOLITROS=None)
        salen, cob = clean(df)
        assert len(salen) == 1

    def test_produccion_nula_excluida(self):
        df = _base(PRODUCCION=None)
        salen, cob = clean(df)
        assert len(salen) == 1

    def test_precio_y_produccion_positivos_valida(self):
        df = _base(PRECIOLITROS=1200.0, PRODUCCION=100.0)
        salen, cob = clean(df)
        assert len(salen) == 0

    def test_finca_valida_no_aparece_en_salen(self):
        df = pd.concat([
            _base(PRECIOLITROS=1200.0, PRODUCCION=100.0),
            _base(IDFINCA="0508602", FINCA="La Fe", PRECIOLITROS=0.0, PRODUCCION=50.0),
        ], ignore_index=True)
        salen, _ = clean(df)
        assert len(salen) == 1
        assert salen.iloc[0]["IDFINCA"] == "0508602"


# ─── Act 17: Construcción de SALEN{PERI} ─────────────────────────────────────

class TestSalenConstruction:
    def test_una_fila_por_finca_excluida(self):
        """4 semanas del mismo IDFINCA excluido → 1 fila en SALEN."""
        rows = pd.concat(
            [_base(IDFINCA="0508602", FINCA="La Fe", PRECIOLITROS=0.0)] * 4,
            ignore_index=True,
        )
        salen, _ = clean(rows)
        assert len(salen) == 1

    def test_salen_tiene_columna_dinamica(self):
        df = _base(PRECIOLITROS=0.0)
        salen, _ = clean(df)
        assert f"SALEN{MES}" in salen.columns

    def test_salen_col_siempre_es_1_por_finca(self):
        """COUNT(DISTINCT FINCA) cuando GROUP BY FINCA = 1 siempre."""
        rows = pd.concat(
            [_base(IDFINCA="0508602", FINCA="La Fe", PRECIOLITROS=0.0)] * 4,
            ignore_index=True,
        )
        salen, _ = clean(rows)
        assert salen.iloc[0][f"SALEN{MES}"] == 1

    def test_salen_columnas_requeridas(self):
        df = _base(PRECIOLITROS=0.0)
        salen, _ = clean(df)
        for col in ["IDFINCA", "DEPARTAMENTO", "COD_MUNI", "MUNICIPIO", "IDDEPMUNI", "FINCA"]:
            assert col in salen.columns, f"Columna {col} faltante en SALEN"

    def test_iddepmuni_sin_espacios(self):
        df = _base(
            PRECIOLITROS=0.0,
            DEPARTAMENTO="Valle Del Cauca",
            MUNICIPIO="Santiago De Cali",
            COD_MUNI="76001",
            COD_DEP="76",
        )
        salen, _ = clean(df)
        assert " " not in salen.iloc[0]["IDDEPMUNI"]
        assert salen.iloc[0]["IDDEPMUNI"] == "ValleDelCaucaSantiagoDeCali"

    def test_idfinca_7_digitos_en_salen(self):
        df = _base(PRECIOLITROS=0.0)
        salen, _ = clean(df)
        assert salen["IDFINCA"].str.match(r"^\d{7}$").all()

    def test_observaciones_col_en_salen(self):
        df = _base(PRECIOLITROS=0.0, observaciones="Sin informacion")
        salen, _ = clean(df)
        assert f"observaciones{MES}" in salen.columns
        assert salen.iloc[0][f"observaciones{MES}"] == "Sin informacion"

    def test_observaciones_nula_cuando_no_hay(self):
        df = _base(PRECIOLITROS=0.0, observaciones=None)
        salen, _ = clean(df)
        assert pd.isna(salen.iloc[0][f"observaciones{MES}"])

    def test_dos_fincas_excluidas_dos_filas(self):
        df = pd.concat([
            _base(IDFINCA="0508601", FINCA="La Esperanza", PRECIOLITROS=0.0),
            _base(IDFINCA="0508602", FINCA="La Fe", PRODUCCION=0.0),
        ], ignore_index=True)
        salen, _ = clean(df)
        assert len(salen) == 2


# ─── Act 19-20: Construcción de COB_{MES} ─────────────────────────────────────

class TestCoberturaConstruction:
    def test_cob_tiene_columnas_dinamicas(self):
        df = _base()
        _, cob = clean(df)
        assert f"V{MES}" in cob.columns
        assert f"NO{MES}" in cob.columns

    def test_cob_columnas_fijas(self):
        df = _base()
        _, cob = clean(df)
        for col in ["DEPARTAMENTO", "COD_MUNI", "MUNICIPIO", "IDDEPMUNI"]:
            assert col in cob.columns, f"Columna {col} faltante en COB"

    def test_cob_vmes_cuenta_fincas_validas(self):
        df = pd.concat([
            _base(IDFINCA="0508601", FINCA="La Esperanza", PRECIOLITROS=1200.0),
            _base(IDFINCA="0508602", FINCA="La Fe",        PRECIOLITROS=1500.0),
        ], ignore_index=True)
        _, cob = clean(df)
        assert cob.iloc[0][f"V{MES}"] == 2

    def test_cob_nomes_cero_cuando_no_hay_excluidas(self):
        df = _base()
        _, cob = clean(df)
        assert cob.iloc[0][f"NO{MES}"] == 0

    def test_cob_nomes_cuenta_fincas_excluidas(self):
        df = pd.concat([
            _base(IDFINCA="0508601", FINCA="F1", PRECIOLITROS=1200.0),
            _base(IDFINCA="0508602", FINCA="F2", PRECIOLITROS=0.0),
            _base(IDFINCA="0508603", FINCA="F3", PRODUCCION=0.0),
        ], ignore_index=True)
        _, cob = clean(df)
        row = cob[cob["MUNICIPIO"] == "Belmira"].iloc[0]
        assert row[f"V{MES}"] == 1
        assert row[f"NO{MES}"] == 2

    def test_cob_iddepmuni_sin_espacios(self):
        df = _base(
            DEPARTAMENTO="Valle Del Cauca",
            MUNICIPIO="Santiago De Cali",
            COD_MUNI="76001",
            COD_DEP="76",
        )
        _, cob = clean(df)
        assert " " not in cob.iloc[0]["IDDEPMUNI"]

    def test_cob_un_municipio_por_municipio(self):
        """Cada municipio aparece exactamente una vez en COB."""
        rows = pd.concat(
            [_base(PRECIOLITROS=float(1000 + i)) for i in range(5)],
            ignore_index=True,
        )
        _, cob = clean(rows)
        assert cob["MUNICIPIO"].duplicated().sum() == 0

    def test_cob_cod_muni_5_digitos(self):
        df = _base()
        _, cob = clean(df)
        assert cob["COD_MUNI"].str.match(r"^\d{5}$").all()


# ─── Act 21: Invariante V{MES} + NO{MES} = total fincas del municipio ─────────

class TestInvarianteCoberturaCompleta:
    def test_total_fincas_igual_validas_mas_excluidas_un_municipio(self):
        """Invariante principal del M3 — Act 21."""
        df = pd.concat([
            _base(IDFINCA="0508601", FINCA="La Esperanza", PRECIOLITROS=1200.0),
            _base(IDFINCA="0508602", FINCA="La Fe",        PRECIOLITROS=1500.0),
            _base(IDFINCA="0508603", FINCA="El Prado",     PRECIOLITROS=0.0),
        ], ignore_index=True)
        _, cob = clean(df)
        row = cob[cob["MUNICIPIO"] == "Belmira"].iloc[0]
        total = row[f"V{MES}"] + row[f"NO{MES}"]
        assert total == 3, f"Esperado 3 fincas totales, obtenido {total}"

    def test_invariante_multiples_municipios(self):
        """V + NO = total en CADA municipio con mezcla de válidas y excluidas."""
        df = pd.concat([
            # Belmira: 2 válidas, 1 excluida
            _base(IDFINCA="0508601", FINCA="F1", MUNICIPIO="Belmira", COD_MUNI="05086", PRECIOLITROS=1200.0),
            _base(IDFINCA="0508602", FINCA="F2", MUNICIPIO="Belmira", COD_MUNI="05086", PRECIOLITROS=1500.0),
            _base(IDFINCA="0508603", FINCA="F3", MUNICIPIO="Belmira", COD_MUNI="05086", PRECIOLITROS=0.0),
            # Medellin: 1 válida, 2 excluidas
            _base(IDFINCA="0500001", FINCA="G1", MUNICIPIO="Medellin", COD_MUNI="05001", PRECIOLITROS=2000.0),
            _base(IDFINCA="0500002", FINCA="G2", MUNICIPIO="Medellin", COD_MUNI="05001", PRECIOLITROS=0.0),
            _base(IDFINCA="0500003", FINCA="G3", MUNICIPIO="Medellin", COD_MUNI="05001", PRODUCCION=0.0),
        ], ignore_index=True)

        _, cob = clean(df)

        belmira = cob[cob["MUNICIPIO"] == "Belmira"].iloc[0]
        assert belmira[f"V{MES}"] == 2
        assert belmira[f"NO{MES}"] == 1

        medellin = cob[cob["MUNICIPIO"] == "Medellin"].iloc[0]
        assert medellin[f"V{MES}"] == 1
        assert medellin[f"NO{MES}"] == 2

    def test_municipio_solo_excluidas_no_aparece_en_cob(self):
        """Un municipio donde TODAS las fincas son excluidas no aparece en COB
        (no hay fincas válidas que lo anclen en VALIDOS)."""
        df = pd.concat([
            _base(IDFINCA="0508601", FINCA="F1", PRECIOLITROS=0.0),
            _base(IDFINCA="0508602", FINCA="F2", PRODUCCION=0.0),
        ], ignore_index=True)
        salen, cob = clean(df)
        assert len(cob) == 0
        assert len(salen) == 2

    def test_municipio_solo_validas_tiene_nomes_cero(self):
        df = pd.concat([
            _base(IDFINCA="0508601", FINCA="F1", PRECIOLITROS=1200.0),
            _base(IDFINCA="0508602", FINCA="F2", PRECIOLITROS=1500.0),
        ], ignore_index=True)
        _, cob = clean(df)
        assert cob.iloc[0][f"NO{MES}"] == 0

    def test_4_semanas_misma_finca_cuenta_como_una(self):
        """Finca con 4 observaciones semanales cuenta 1 en V{MES}, no 4."""
        rows = pd.concat(
            [_base(IDFINCA="0508601", FINCA="La Esperanza", PRECIOLITROS=1200.0)] * 4,
            ignore_index=True,
        )
        _, cob = clean(rows)
        assert cob.iloc[0][f"V{MES}"] == 1


# ─── Act 18: Exportación Excel ────────────────────────────────────────────────

class TestExportarExcluidasXlsx:
    def test_retorna_mismo_dataframe(self):
        salen, _ = clean(_base(PRECIOLITROS=0.0))
        result = exportar_excluidas_xlsx(salen)
        pd.testing.assert_frame_equal(result, salen)

    def test_retorna_dataframe_vacio_cuando_no_hay_excluidas(self):
        salen, _ = clean(_base())
        result = exportar_excluidas_xlsx(salen)
        assert len(result) == 0
