"""Tests del pipeline panel - M9: panel trimestral de fincas lecheras."""
from __future__ import annotations

import pandas as pd
import pytest

from sipsa_leche.pipelines.panel.nodes import (
    compute_panel_prices,
    compute_panel_weights,
    construir_panel_trimestral,
    merge_panel_with_current,
    summarize_panel_total,
)

MES_A = "MAR"
MES_ANT = "FEB"


def _panel_anterior() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "IDFINCA": "0508601",
                "T_VACAS_FEB": 10.0,
                "T_PROD_FEB": 100.0,
                "MED_FINCA_FEB": 1000.0,
            },
            {
                "IDFINCA": "0508602",
                "T_VACAS_FEB": 20.0,
                "T_PROD_FEB": 300.0,
                "MED_FINCA_FEB": 2000.0,
            },
            {
                "IDFINCA": "0508603",
                "T_VACAS_FEB": 30.0,
                "T_PROD_FEB": 500.0,
                "MED_FINCA_FEB": 3000.0,
            },
        ]
    )


def _finca_actual() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "IDFINCA": "0508601",
                "T_VACAS_MAR": 11.0,
                "T_PROD_MAR": 200.0,
                "MED_FINCA_MAR": 1200.0,
            },
            {
                "IDFINCA": "0508602",
                "T_VACAS_MAR": 21.0,
                "T_PROD_MAR": 600.0,
                "MED_FINCA_MAR": 2200.0,
            },
            {
                "IDFINCA": "0508604",
                "T_VACAS_MAR": 41.0,
                "T_PROD_MAR": 800.0,
                "MED_FINCA_MAR": 4200.0,
            },
        ]
    )


class TestMergePanel:
    def test_conserva_solo_fincas_en_ambos_meses(self):
        out = merge_panel_with_current(_panel_anterior(), _finca_actual(), MES_A, MES_ANT)

        assert out["IDFINCA"].tolist() == ["0508601", "0508602"]

    def test_agrega_columnas_del_mes_actual(self):
        out = merge_panel_with_current(_panel_anterior(), _finca_actual(), MES_A, MES_ANT)

        assert "T_PROD_FEB" in out.columns
        assert "T_PROD_MAR" in out.columns
        assert out.loc[out["IDFINCA"] == "0508601", "T_PROD_MAR"].iloc[0] == pytest.approx(200.0)

    def test_rechaza_idfinca_duplicado(self):
        panel = pd.concat([_panel_anterior(), _panel_anterior().iloc[[0]]], ignore_index=True)

        with pytest.raises(ValueError, match="duplicados"):
            merge_panel_with_current(panel, _finca_actual(), MES_A, MES_ANT)


class TestPanelWeights:
    def test_tprod2_aplica_ajuste_nd(self):
        panel = merge_panel_with_current(_panel_anterior(), _finca_actual(), MES_A, MES_ANT)
        out = compute_panel_weights(panel, MES_A, MES_ANT, n1=2, d1=5, n2=1, d2=4)

        assert out.loc[0, "T_PROD2_FEB"] == pytest.approx(140.0)
        assert out.loc[0, "T_PROD2_MAR"] == pytest.approx(250.0)

    def test_pesos_suman_uno_por_mes(self):
        panel = merge_panel_with_current(_panel_anterior(), _finca_actual(), MES_A, MES_ANT)
        out = compute_panel_weights(panel, MES_A, MES_ANT)

        assert out["P_FEB"].sum() == pytest.approx(1.0)
        assert out["P_MAR"].sum() == pytest.approx(1.0)

    def test_denominador_cero_falla(self):
        panel = merge_panel_with_current(_panel_anterior(), _finca_actual(), MES_A, MES_ANT)

        with pytest.raises(ValueError, match="D1"):
            compute_panel_weights(panel, MES_A, MES_ANT, n1=1, d1=0)


class TestPanelPricesAndTotal:
    def test_pre_es_precio_por_participacion(self):
        panel = merge_panel_with_current(_panel_anterior(), _finca_actual(), MES_A, MES_ANT)
        weighted = compute_panel_weights(panel, MES_A, MES_ANT)
        out = compute_panel_prices(weighted, MES_A, MES_ANT)

        assert out.loc[out["IDFINCA"] == "0508601", "PRE_FEB"].iloc[0] == pytest.approx(250.0)
        assert out.loc[out["IDFINCA"] == "0508602", "PRE_FEB"].iloc[0] == pytest.approx(1500.0)
        assert out["PRE_FEB"].sum() == pytest.approx(1750.0)

    def test_total_resume_sumas_proc_tabulado(self):
        panel = merge_panel_with_current(_panel_anterior(), _finca_actual(), MES_A, MES_ANT)
        weighted = compute_panel_weights(panel, MES_A, MES_ANT, n1=2, d1=5, n2=1, d2=4)
        priced = compute_panel_prices(weighted, MES_A, MES_ANT)
        total = summarize_panel_total(priced, MES_A, MES_ANT)

        assert total.loc[0, "N_FINCAS_PANEL"] == 2
        assert total.loc[0, "PRE_FEB"] == pytest.approx(priced["PRE_FEB"].sum())
        assert total.loc[0, "PRE_MAR"] == pytest.approx(priced["PRE_MAR"].sum())
        assert total.loc[0, "T_PROD2_FEB"] == pytest.approx(560.0)
        assert total.loc[0, "T_PROD2_MAR"] == pytest.approx(1000.0)

    def test_nodo_principal_retorna_detalle_y_total(self):
        detalle, total = construir_panel_trimestral(
            _panel_anterior(),
            _finca_actual(),
            MES_A,
            MES_ANT,
            {"N1": 2, "D1": 5, "N2": 1, "D2": 4},
        )

        assert len(detalle) == 2
        assert len(total) == 1
        assert set(["PRE_FEB", "PRE_MAR", "T_PROD2_FEB", "T_PROD2_MAR"]).issubset(detalle.columns)
