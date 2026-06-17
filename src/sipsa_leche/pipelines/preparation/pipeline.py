"""Pipeline preparation — M1: Preparación del archivo Excel de entrada.

DAG:
    params:nombre_base ──┐
    params:mes_nombre  ──┴─► [preparar_hoja_excel] ──► base_excel_preparado
                                                         ├─► [guardar_cabeceras] ──► cabeceras_referencia
                                                         └─► [validar_semanas]   ──► semanas_validacion

``base_excel_preparado`` es un MemoryDataset compartido con el nodo
``snapshot_raw`` del pipeline ingestion; no requiere entrada en catalog.yml.
"""
from __future__ import annotations

from kedro.pipeline import Pipeline, node, pipeline

from sipsa_leche.pipelines.preparation.nodes import (
    guardar_cabeceras,
    preparar_hoja_excel,
    validar_semanas,
)


def create_pipeline(**kwargs) -> Pipeline:
    return pipeline(
        [
            node(
                func=preparar_hoja_excel,
                inputs=["params:nombre_base", "params:mes_nombre"],
                outputs="base_excel_preparado",
                name="preparar_hoja_excel",
                tags=["m1", "preparation"],
            ),
            node(
                func=guardar_cabeceras,
                inputs="base_excel_preparado",
                outputs="cabeceras_referencia",
                name="guardar_cabeceras",
                tags=["m1", "preparation"],
            ),
            node(
                func=validar_semanas,
                inputs=["base_excel_preparado", "params:periodo", "params:mes_nombre"],
                outputs="semanas_validacion",
                name="validar_semanas",
                tags=["m1", "preparation", "validation"],
            ),
        ]
    )
