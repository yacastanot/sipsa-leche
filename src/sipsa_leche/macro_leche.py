"""Pipeline SIPSA Leche — referencia de nodos y flujo de trabajo mensual.

════════════════════════════════════════════════════════════════════
FLUJO DE TRABAJO MENSUAL
════════════════════════════════════════════════════════════════════

  PASO 0 — Actualizar parámetros para el nuevo mes:
      sipsa-periodo --periodo 042026
      (o: python -m sipsa_leche.utils.actualizar_periodo --periodo 042026)

  PASO 1 — Colocar el Excel en data/01_raw/:
      data/01_raw/BASE042026.xlsx

  PASO 2 — Ejecutar el pipeline completo:
      kedro run

════════════════════════════════════════════════════════════════════
PIPELINES Y NODOS (M1 → M10)
════════════════════════════════════════════════════════════════════

  preparation (M1)
      preparar_hoja_excel  → BASE{PERIODO}_ok.xlsx  (hoja renombrada al mes)
      guardar_cabeceras    → data/01_raw/cabeceras_{PERIODO}.csv
      validar_semanas      → data/01_raw/semanas_{PERIODO}.csv

  ingestion (M2)
      snapshot_raw         → base_peri_raw  (bronze parquet)

  cleaning (M2)
      depurar_base         → base_peri_clean  (correcciones IDFINCA + asignación macroregión)

  coverage (M3)
      calcular_cobertura   → cobertura_mes, excluidas_mes

  farm_price (M4)
      calcular_precio_finca → FINCA_{MES}.parquet

  municipality_price (M5)
      calcular_precio_municipio → MUNICIPIO_{MES}.parquet

  dept_macro_price (M6)
      calcular_precio_departamento → DEPARTAMENTO_{MES}.parquet
      calcular_precio_macro        → MACRO_{MES}.parquet

  monthly_variation (M7)
      calcular_variacion_*  → MUESTRA/FINCA/MUNICIPIO/DEP/MACRO variación mensual
      Nota: la variación de cobertura usa cob_actual ✕ cob_anterior (no cob ✕ cob)

  correlation (M8)
      calcular_correlaciones → CORMUNI_{MES}.parquet, CORDEP_{MES}.parquet

  panel (M9)
      construir_panel_trimestral → PANEL_{MES}.parquet

  outputs (M10)
      generar_cuadros_salida    → CUADROS_{PERI}_TOT.xlsx, CUADROS_{PERI}.xlsx,
                                   COBERTURA.xlsx
      verificar_duplicados_finca → DUPLICADOS_IDFINCA_{PERI}.xlsx (vacío si OK)

  cuentas_nacionales (M11) — pipeline independiente para DSCN
      calcular_semanas_operativo → n_semanas
      calcular_excluidas         → Excluidas_leche_{PERI}.xlsx
      generar_leche_cruda        → LECHE_CRUDA_{PERI}.xlsx (LECHE CRUDA + LecheDANE;
                                     hoja trimes se actualiza manualmente en Excel)

════════════════════════════════════════════════════════════════════
COMANDOS RÁPIDOS
════════════════════════════════════════════════════════════════════

  kedro run                                   # pipeline completo (M1-M10)
  kedro run --pipeline preparation            # M1: renombrar hoja, cabeceras, validar SEMANA
  kedro run --pipeline ingestion              # M1+M2: preparation + snapshot bronze
  kedro run --pipeline silver                 # M1-M6: hasta precios por nivel
  kedro run --pipeline gold_outputs           # M7-M10: variación, correlación, panel, XLSX
  kedro run --pipeline outputs                # solo M10: regenerar cuadros XLSX
  kedro run --pipeline cuentas_nacionales     # M11: Leche Cruda y Excluidas para DSCN
"""
from __future__ import annotations

# Re-exportar funciones clave para uso en notebooks o scripts externos
from sipsa_leche.utils.actualizar_periodo import actualizar_periodo
from sipsa_leche.pipelines.cleaning.nodes import depurar_base
from sipsa_leche.pipelines.correlation.nodes import calcular_correlaciones
from sipsa_leche.pipelines.coverage.nodes import calcular_cobertura
from sipsa_leche.pipelines.dept_macro_price.nodes import (
    calcular_precio_departamento,
    calcular_precio_macro,
)
from sipsa_leche.pipelines.farm_price.nodes import calcular_precio_finca
from sipsa_leche.pipelines.monthly_variation.nodes import (
    calcular_variacion_cobertura,
    calcular_variacion_departamento,
    calcular_variacion_finca,
    calcular_variacion_macro,
    calcular_variacion_municipio,
)
from sipsa_leche.pipelines.municipality_price.nodes import calcular_precio_municipio
from sipsa_leche.pipelines.panel.nodes import construir_panel_trimestral
from sipsa_leche.pipelines.preparation.nodes import (
    guardar_cabeceras,
    preparar_hoja_excel,
    validar_semanas,
)
from sipsa_leche.pipelines.cuentas_nacionales.nodes import (
    calcular_semanas_operativo,
    calcular_excluidas,
    generar_leche_cruda,
)

__all__ = [
    # Paso 0 — actualización de parámetros del período
    "actualizar_periodo",
    # M1 — preparation
    "preparar_hoja_excel",
    "guardar_cabeceras",
    "validar_semanas",
    # M2 — cleaning (%VALIDACION asignación MACRO + depuración)
    "depurar_base",
    # M3 — coverage (%VALIDACION cobertura y excluidas)
    "calcular_cobertura",
    # M4 — farm_price (%CUADROS FINCA)
    "calcular_precio_finca",
    # M5 — municipality_price (%CUADROS MUNICIPIO)
    "calcular_precio_municipio",
    # M6 — dept_macro_price (%CUADROS DEPARTAMENTO + MACROREGION)
    "calcular_precio_departamento",
    "calcular_precio_macro",
    # M7 — monthly_variation (%COMPARACION)
    "calcular_variacion_cobertura",
    "calcular_variacion_finca",
    "calcular_variacion_municipio",
    "calcular_variacion_departamento",
    "calcular_variacion_macro",
    # M8 — correlation (%COR)
    "calcular_correlaciones",
    # M9 — panel (%PANEL)
    "construir_panel_trimestral",
    # M11 — cuentas_nacionales (DSCN)
    "calcular_semanas_operativo",
    "calcular_excluidas",
    "generar_leche_cruda",
]
