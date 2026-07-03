# 01 · Arquitectura

## Propósito del sistema

Automatiza el procesamiento mensual del operativo de precios al productor de leche
cruda del SIPSA (DANE). Reemplaza el flujo SAS (`MARZO_2026.sas`, `MACRO LECHE.sas`)
con un pipeline Python reproducible, versionado y auditable.

## Diagrama de componentes

```
BASE{MMYYYY}.xlsx
      │
      ▼
┌─────────────────────────────────────────────────────────┐
│  BRONZE — data/01_raw/                                  │
│  Archivo de campo sin transformar                       │
└─────────────────────────────────────────────────────────┘
      │  Kedro pipeline "ingestion"
      ▼
┌─────────────────────────────────────────────────────────┐
│  SILVER — data/03_primary/ · data/04_feature/           │
│  M2 Ingesta → M3 Cobertura → M4 Finca → M5 Municipio   │
│  → M6 Depto/Macro → M7 Variación → M8 Correlación      │
│  → M9 Panel trimestral                                  │
└─────────────────────────────────────────────────────────┘
      │  Kedro pipeline "outputs"
      ▼
┌─────────────────────────────────────────────────────────┐
│  GOLD — data/08_reporting/                              │
│  CUADROS_{PERI}.xlsx     (publicación — FINCA oculta)  │
│  CUADROS_{PERI}_TOT.xlsx (análisis interno)             │
│  COBERTURA.xlsx                                         │
└─────────────────────────────────────────────────────────┘
```

## Tecnologías elegidas y por qué

| Tecnología | Razón |
|---|---|
| **Kedro 0.19.15** | Trazabilidad de datos, catálogo declarativo, pipelines modulares |
| **pandas** | Equivalente vectorizado a las macros SAS de agregación |
| **openpyxl** | Formato de publicación (celdas combinadas, ancho de columnas, hoja oculta) |
| **ruamel.yaml** | Edición de YAML preservando comentarios en `parameters.yml` |
| **structlog** | Logs estructurados con contexto, auditables en producción |
| **FastAPI** | API web para operación sin terminal (carga, configuración, ejecución) |
| **Parquet** | Formato intermedio eficiente y tipado para capas Silver/Gold |

## Decisiones de diseño

### Configuración como única fuente de verdad

Todos los parámetros que cambian mensualmente están en `conf/base/parameters.yml`
y `conf/base/globals.yml`. El código **nunca tiene valores de mes hardcodeados**.
La herramienta `sipsa-periodo --periodo MMAAAA` actualiza ambos archivos automáticamente.

### Umbrales de tendencia configurables

Los cortes `xxx / xx / x / = / ° / °° / °°°` del precio están en `parameters.yml`
(`tendencia_umbral_finca_muni` y `tendencia_umbral_dep_macro`) y no en el código.
Cambian con metodología sin tocar `src/`.

### Equivalencia SAS verificable

Cada nodo documenta la línea de SAS que reemplaza. Los tests de regresión
(`tests/regression/`) comparan las salidas Python con las salidas SAS de referencia
dentro de la tolerancia `regresion_tolerancia` (por defecto 0.0001).

### Sin dependencias de SAS en el flujo Python

El flujo de trabajo Python es completamente autónomo. Los archivos `.sas` históricos
se mantienen como referencia en la carpeta de documentación, pero no se leen ni
ejecutan en ningún paso del pipeline.
