"""Pipeline municipality_price — M5: Precio medio del litro de leche por municipio.

DAG:
    base_peri_clean ──► [calcular_precio_municipio] ──► municipio_mes
         ▲
    params:mes_actual
"""
from __future__ import annotations

from kedro.pipeline import Pipeline, node, pipeline

from sipsa_leche.pipelines.municipality_price.nodes import calcular_precio_municipio


def create_pipeline(**kwargs) -> Pipeline:
    return pipeline(
        [
            node(
                func=calcular_precio_municipio,
                inputs=["base_peri_clean", "params:mes_actual"],
                outputs="municipio_mes",
                name="calcular_precio_municipio",
                tags=["m5", "municipality_price", "silver"],
            ),
        ]
    )
