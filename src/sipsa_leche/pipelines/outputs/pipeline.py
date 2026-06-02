"""Pipeline outputs — M10: Cuadros de salida para publicación.

DAG:
    variacion_finca + variacion_municipio + variacion_departamento
    + variacion_macro + variacion_cobertura
    + params:mes_actual + params:mes_anterior + params:periodo
    ──► [generar_cuadros_salida] ──► cuadros_log
"""
from __future__ import annotations

from kedro.pipeline import Pipeline, node, pipeline

from sipsa_leche.pipelines.outputs.nodes import generar_cuadros_salida


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
        ]
    )
