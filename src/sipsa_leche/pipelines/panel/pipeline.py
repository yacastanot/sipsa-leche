"""Pipeline panel - M9: panel trimestral de fincas lecheras.

DAG:
    panel_persistido + finca_mes
        -> [construir_panel_trimestral]
        -> panel_actualizado + panel_total
"""
from __future__ import annotations

from kedro.pipeline import Pipeline, node, pipeline

from sipsa_leche.pipelines.panel.nodes import construir_panel_trimestral


def create_pipeline(**kwargs) -> Pipeline:
    return pipeline(
        [
            node(
                func=construir_panel_trimestral,
                inputs=[
                    "panel_persistido",
                    "finca_mes",
                    "params:mes_actual",
                    "params:mes_anterior",
                    "params:panel_ajuste",
                ],
                outputs=["panel_actualizado", "panel_total"],
                name="construir_panel_trimestral",
                tags=["m9", "panel", "gold"],
            ),
        ]
    )
