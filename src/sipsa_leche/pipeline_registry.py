"""Registro de pipelines del proyecto SIPSA Leche.

Organización por módulos del cronograma de migración SAS → Python/Kedro:
  M1:  preparation               (Renombrado de hoja Excel + cabeceras de referencia)
  M2:  ingestion + cleaning      (Lectura y depuración de la encuesta)
  M3:  coverage                  (Cobertura y fincas excluidas)
  M4:  farm_price                (Precio mensual por finca)
  M5:  municipality_price        (Precio medio por municipio)
  M6:  dept_macro_price          (Precio por departamento y macrorregión)
  M7:  monthly_variation         (Variación mensual — corrige bug SAS línea 116)
  M8:  correlation               (Correlación precio vs producción/venta)
  M9:  panel                     (Panel trimestral de fincas)
  M10: outputs                   (Cuadros XLSX de publicación)
  M11: cuentas_nacionales        (Leche Cruda y Excluidas para DSCN)
"""
from __future__ import annotations

from kedro.pipeline import Pipeline

from sipsa_leche.pipelines.cleaning import create_pipeline as cleaning_pipeline
from sipsa_leche.pipelines.correlation import create_pipeline as correlation_pipeline
from sipsa_leche.pipelines.coverage import create_pipeline as coverage_pipeline
from sipsa_leche.pipelines.cuentas_nacionales import (
    create_pipeline as cuentas_pipeline,
)
from sipsa_leche.pipelines.dept_macro_price import (
    create_pipeline as dept_macro_pipeline,
)
from sipsa_leche.pipelines.farm_price import create_pipeline as farm_pipeline
from sipsa_leche.pipelines.ingestion import create_pipeline as ingestion_pipeline
from sipsa_leche.pipelines.monthly_variation import (
    create_pipeline as variation_pipeline,
)
from sipsa_leche.pipelines.municipality_price import create_pipeline as muni_pipeline
from sipsa_leche.pipelines.outputs import create_pipeline as outputs_pipeline
from sipsa_leche.pipelines.panel import create_pipeline as panel_pipeline
from sipsa_leche.pipelines.preparation import create_pipeline as preparation_pipeline


def register_pipelines() -> dict[str, Pipeline]:
    """Registra todos los pipelines del proyecto SIPSA Leche.

    Pipelines disponibles:
      __default__        : Pipeline completo (preparación → publicación + DSCN)
      silver             : Solo capas Raw → Silver (sin comparaciones intermensuales)
      gold_outputs       : Capa Gold + generación de reportes XLSX
      preparation        : Solo M1 — renombra hoja Excel y guarda cabeceras de referencia
      ingestion          : M1 + M2 — preparación y snapshot bronze
      cleaning           : Solo depuración y reglas de negocio
      coverage           : Solo cobertura y fincas excluidas
      farm_price         : Solo precio medio por finca
      muni_price         : Solo precio medio por municipio
      dept_macro         : Solo precio por departamento y macrorregión
      variation          : Solo variación mensual (M7)
      correlation        : Solo correlaciones (M8)
      panel              : Solo panel trimestral (M9)
      outputs            : Solo generación de XLSX (M10)
      cuentas_nacionales : Solo reportes DSCN (M11) — requiere M7 ejecutado
    """
    _preparation  = preparation_pipeline()
    _ingestion    = ingestion_pipeline()
    _cleaning     = cleaning_pipeline()
    _coverage     = coverage_pipeline()
    _farm         = farm_pipeline()
    _muni         = muni_pipeline()
    _dept_macro   = dept_macro_pipeline()
    _variation    = variation_pipeline()
    _correlation  = correlation_pipeline()
    _panel        = panel_pipeline()
    _outputs      = outputs_pipeline()
    _cuentas      = cuentas_pipeline()

    return {
        "__default__": (
            _preparation + _ingestion + _cleaning + _coverage
            + _farm + _muni + _dept_macro
            + _variation + _correlation + _panel + _outputs
            + _cuentas
        ),
        # Pipelines parciales para ejecución selectiva
        "silver": (
            _preparation + _ingestion + _cleaning + _coverage
            + _farm + _muni + _dept_macro
        ),
        "gold_outputs": _variation + _correlation + _panel + _outputs + _cuentas,
        # Pipelines individuales por módulo
        "preparation":        _preparation,
        "ingestion":          _preparation + _ingestion,
        "cleaning":           _cleaning,
        "coverage":           _coverage,
        "farm_price":         _farm,
        "muni_price":         _muni,
        "dept_macro":         _dept_macro,
        "variation":          _variation,
        "correlation":        _correlation,
        "panel":              _panel,
        "outputs":            _outputs,
        "cuentas_nacionales": _cuentas,
    }
