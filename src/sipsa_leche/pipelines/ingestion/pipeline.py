"""Pipeline ingestion — M2: Lectura de la Encuesta de Leche Cruda en Finca.

DAG:
    base_excel_preparado ──► [snapshot_raw] ──► base_peri_raw

``base_excel_preparado`` es producido por el pipeline preparation (M1).
"""
from __future__ import annotations

from kedro.pipeline import Pipeline, node, pipeline

from sipsa_leche.pipelines.ingestion.nodes import snapshot_raw


def create_pipeline(**kwargs) -> Pipeline:
    return pipeline(
        [
            node(
                func=snapshot_raw,
                inputs="base_excel_preparado",
                outputs="base_peri_raw",
                name="snapshot_raw",
                tags=["m2", "ingestion", "bronze"],
            ),
        ]
    )
