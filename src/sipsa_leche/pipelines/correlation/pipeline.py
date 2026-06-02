"""Pipeline correlation — M8: Correlación precio vs producción/venta.

DAG:
    base_peri_clean ──► [calcular_correlaciones] ──► correlacion_municipio
         ▲                                       └──► correlacion_departamento
    params:mes_actual
"""
from __future__ import annotations

from kedro.pipeline import Pipeline, node, pipeline

from sipsa_leche.pipelines.correlation.nodes import calcular_correlaciones


def create_pipeline(**kwargs) -> Pipeline:
    return pipeline(
        [
            node(
                func=calcular_correlaciones,
                inputs=["base_peri_clean", "params:mes_actual"],
                outputs=["correlacion_municipio", "correlacion_departamento"],
                name="calcular_correlaciones",
                tags=["m8", "correlation", "gold"],
            ),
        ]
    )
