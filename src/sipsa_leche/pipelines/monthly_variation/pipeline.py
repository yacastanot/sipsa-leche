"""Pipeline monthly_variation — M7: Variación mensual del precio y la producción de leche.

DAG:
    cobertura_mes + cobertura_mes_anterior  → [var_cobertura]   → variacion_cobertura
    finca_mes    + finca_mes_anterior       → [var_finca]       → variacion_finca
    municipio_mes + municipio_mes_anterior  → [var_municipio]   → variacion_municipio
    departamento_mes + dep_mes_anterior     → [var_departamento]→ variacion_departamento
    macro_mes   + macro_mes_anterior        → [var_macro]       → variacion_macro

Todos los nodos leen también params:mes_actual, params:mes_anterior y
params:tendencia_umbral_finca_muni / params:tendencia_umbral_dep_macro.
"""
from __future__ import annotations

from kedro.pipeline import Pipeline, node, pipeline

from sipsa_leche.pipelines.monthly_variation.nodes import (
    calcular_variacion_cobertura,
    calcular_variacion_departamento,
    calcular_variacion_finca,
    calcular_variacion_macro,
    calcular_variacion_municipio,
)


def create_pipeline(**kwargs) -> Pipeline:
    return pipeline(
        [
            node(
                func=calcular_variacion_cobertura,
                inputs=[
                    "cobertura_mes",
                    "cobertura_mes_anterior",
                    "params:mes_actual",
                    "params:mes_anterior",
                ],
                outputs="variacion_cobertura",
                name="calcular_variacion_cobertura",
                tags=["m7", "variation", "gold"],
            ),
            node(
                func=calcular_variacion_finca,
                inputs=[
                    "finca_mes",
                    "finca_mes_anterior",
                    "params:mes_actual",
                    "params:mes_anterior",
                    "params:tendencia_umbral_finca_muni",
                ],
                outputs="variacion_finca",
                name="calcular_variacion_finca",
                tags=["m7", "variation", "gold"],
            ),
            node(
                func=calcular_variacion_municipio,
                inputs=[
                    "municipio_mes",
                    "municipio_mes_anterior",
                    "params:mes_actual",
                    "params:mes_anterior",
                    "params:tendencia_umbral_finca_muni",
                ],
                outputs="variacion_municipio",
                name="calcular_variacion_municipio",
                tags=["m7", "variation", "gold"],
            ),
            node(
                func=calcular_variacion_departamento,
                inputs=[
                    "departamento_mes",
                    "departamento_mes_anterior",
                    "params:mes_actual",
                    "params:mes_anterior",
                    "params:tendencia_umbral_dep_macro",
                ],
                outputs="variacion_departamento",
                name="calcular_variacion_departamento",
                tags=["m7", "variation", "gold"],
            ),
            node(
                func=calcular_variacion_macro,
                inputs=[
                    "macro_mes",
                    "macro_mes_anterior",
                    "params:mes_actual",
                    "params:mes_anterior",
                    "params:tendencia_umbral_dep_macro",
                ],
                outputs="variacion_macro",
                name="calcular_variacion_macro",
                tags=["m7", "variation", "gold"],
            ),
        ]
    )
