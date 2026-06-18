"""Pipeline cuentas_nacionales — M11: Reportes de Leche Cruda para DSCN.

DAG:
    semanas_validacion                            → [calcular_semanas_operativo] → n_semanas_operativo
    variacion_finca + ruta_excluidas + params     → [calcular_excluidas]         → total_excluidas_mes
    variacion_macro + total_excluidas_mes
        + n_semanas_operativo + ruta_base + params → [generar_leche_cruda]        → leche_cruda_resumen

Salidas en data/08_reporting/:
    LECHE_CRUDA_{PERI}.xlsx
    Excluidas_leche_{PERI}.xlsx
"""
from __future__ import annotations

from kedro.pipeline import Pipeline, node, pipeline

from sipsa_leche.pipelines.cuentas_nacionales.nodes import (
    calcular_excluidas,
    calcular_semanas_operativo,
    generar_leche_cruda,
)


def create_pipeline(**kwargs) -> Pipeline:
    return pipeline(
        [
            node(
                func=calcular_semanas_operativo,
                inputs=["semanas_validacion"],
                outputs="n_semanas_operativo",
                name="calcular_semanas_operativo",
                tags=["m11", "cuentas_nacionales"],
            ),
            node(
                func=calcular_excluidas,
                inputs=[
                    "variacion_finca",
                    "params:ruta_excluidas",
                    "params:periodo",
                    "params:mes_actual",
                    "params:mes_anterior",
                ],
                outputs="total_excluidas_mes",
                name="calcular_excluidas",
                tags=["m11", "cuentas_nacionales"],
            ),
            node(
                func=generar_leche_cruda,
                inputs=[
                    "variacion_macro",
                    "total_excluidas_mes",
                    "n_semanas_operativo",
                    "params:ruta_leche_cruda_base",
                    "params:periodo",
                    "params:mes_actual",
                ],
                outputs="leche_cruda_resumen",
                name="generar_leche_cruda",
                tags=["m11", "cuentas_nacionales"],
            ),
        ]
    )
