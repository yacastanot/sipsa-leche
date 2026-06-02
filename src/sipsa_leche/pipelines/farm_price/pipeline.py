"""Pipeline farm_price — M4: Precio mensual del litro de leche por finca.

DAG:
    base_peri_clean ──► [calcular_precio_finca] ──► finca_mes
         ▲
    params:mes_actual
"""
from __future__ import annotations

from kedro.pipeline import Pipeline, node, pipeline

from sipsa_leche.pipelines.farm_price.nodes import calcular_precio_finca


def create_pipeline(**kwargs) -> Pipeline:
    return pipeline(
        [
            node(
                func=calcular_precio_finca,
                inputs=["base_peri_clean", "params:mes_actual"],
                outputs="finca_mes",
                name="calcular_precio_finca",
                tags=["m4", "farm_price", "silver"],
            ),
        ]
    )
