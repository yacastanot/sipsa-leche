"""Pipeline cleaning — SIPSA Leche.

Pendiente de implementación. Módulo correspondiente según cronograma:
  ingestion / cleaning         → M2: Lectura y depuración de la encuesta
  coverage                     → M3: Cobertura y fincas excluidas
  farm_price                   → M4: Precio mensual por finca
  municipality_price           → M5: Precio medio por municipio
  dept_macro_price             → M6: Precio por departamento y macrorregión
  monthly_variation            → M7: Variación mensual precio y producción
  correlation                  → M8: Correlación precio vs producción/venta
  panel                        → M9: Panel trimestral de fincas
  outputs                      → M10: Cuadros de salida para publicación
"""
from __future__ import annotations

from kedro.pipeline import Pipeline, pipeline


def create_pipeline(**kwargs) -> Pipeline:
    return pipeline([])
