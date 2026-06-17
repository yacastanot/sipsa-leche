"""Pipeline outputs — M10: Cuadros de salida para publicación.

DAG:
    variacion_finca + variacion_municipio + variacion_departamento
    + variacion_macro + variacion_cobertura
    + params:mes_actual + params:mes_anterior + params:periodo
    ──► [generar_cuadros_salida]     ──► cuadros_log

    variacion_finca + finca_mes + finca_mes_anterior
    + params:mes_actual + params:mes_anterior + params:periodo
    ──► [verificar_duplicados_finca] ──► duplicados_finca
"""
from __future__ import annotations

from kedro.pipeline import Pipeline, node, pipeline

from sipsa_leche.pipelines.outputs.nodes import (
    generar_cuadros_salida,
    verificar_duplicados_finca,
)


def create_pipeline(**kwargs) -> Pipeline:
    return pipeline(
        [
            node(
                func=generar_cuadros_salida,
                inputs=[
                    "variacion_finca",
                    "variacion_municipio",
                    "variacion_departamento",
                    "variacion_macro",
                    "variacion_cobertura",
                    "params:mes_actual",
                    "params:mes_anterior",
                    "params:periodo",
                ],
                outputs="cuadros_log",
                name="generar_cuadros_salida",
                tags=["m10", "outputs", "reporting"],
            ),
            node(
                func=verificar_duplicados_finca,
                inputs=[
                    "variacion_finca",
                    "finca_mes",
                    "finca_mes_anterior",
                    "params:mes_actual",
                    "params:mes_anterior",
                    "params:periodo",
                ],
                outputs="duplicados_finca",
                name="verificar_duplicados_finca",
                tags=["m10", "outputs", "calidad"],
            ),
        ]
    )
