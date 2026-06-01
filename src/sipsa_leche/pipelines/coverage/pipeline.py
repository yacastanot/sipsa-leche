"""Pipeline coverage — M3: Cobertura y fincas excluidas del cálculo.

DAG:
    base_peri_clean ──► [calcular_cobertura] ──► excluidas_mes
         ▲                                   └──► cobertura_mes
    params:mes_actual
                        excluidas_mes ──► [exportar_excluidas_xlsx] ──► excluidas_xlsx
"""
from __future__ import annotations

from kedro.pipeline import Pipeline, node, pipeline

from sipsa_leche.pipelines.coverage.nodes import (
    calcular_cobertura,
    exportar_excluidas_xlsx,
)


def create_pipeline(**kwargs) -> Pipeline:
    return pipeline(
        [
            node(
                func=calcular_cobertura,
                inputs=["base_peri_clean", "params:mes_actual"],
                outputs=["excluidas_mes", "cobertura_mes"],
                name="calcular_cobertura",
                tags=["m3", "coverage", "silver"],
            ),
            node(
                func=exportar_excluidas_xlsx,
                inputs="excluidas_mes",
                outputs="excluidas_xlsx",
                name="exportar_excluidas_xlsx",
                tags=["m3", "coverage", "reporting"],
            ),
        ]
    )
