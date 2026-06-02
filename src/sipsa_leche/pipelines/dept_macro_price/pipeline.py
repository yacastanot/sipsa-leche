"""Pipeline dept_macro_price — M6: Precio por departamento y macrorregión lechera.

DAG:
    base_peri_clean ──► [calcular_precio_departamento] ──► departamento_mes
         ▲
    params:mes_actual
    base_peri_clean ──► [calcular_precio_macro]         ──► macro_mes
         ▲
    params:mes_actual
"""
from __future__ import annotations

from kedro.pipeline import Pipeline, node, pipeline

from sipsa_leche.pipelines.dept_macro_price.nodes import (
    calcular_precio_departamento,
    calcular_precio_macro,
)


def create_pipeline(**kwargs) -> Pipeline:
    return pipeline(
        [
            node(
                func=calcular_precio_departamento,
                inputs=["base_peri_clean", "params:mes_actual"],
                outputs="departamento_mes",
                name="calcular_precio_departamento",
                tags=["m6", "dept_price", "silver"],
            ),
            node(
                func=calcular_precio_macro,
                inputs=["base_peri_clean", "params:mes_actual"],
                outputs="macro_mes",
                name="calcular_precio_macro",
                tags=["m6", "macro_price", "silver"],
            ),
        ]
    )
