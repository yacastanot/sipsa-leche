"""Pipeline cleaning — M2: Depuración de la Encuesta de Leche Cruda en Finca.

DAG:
    base_peri_raw ──► [depurar_base] ──► base_peri_clean
                           ▲
               params:idfinca_corrections
               params:macroregiones
"""
from __future__ import annotations

from kedro.pipeline import Pipeline, node, pipeline

from sipsa_leche.pipelines.cleaning.nodes import depurar_base


def create_pipeline(**kwargs) -> Pipeline:
    return pipeline(
        [
            node(
                func=depurar_base,
                inputs=[
                    "base_peri_raw",
                    "params:idfinca_corrections",
                    "params:macroregiones",
                ],
                outputs="base_peri_clean",
                name="depurar_base",
                tags=["m2", "cleaning", "silver"],
            ),
        ]
    )
