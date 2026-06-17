# 05 · Flujo de datos

## Pipeline de extremo a extremo

```
Entrada: data/01_raw/BASE{MMYYYY}.xlsx
         data/03_primary/PANEL.parquet         (panel trimestral del mes anterior)
         conf/base/parameters.yml              (umbrales, macroregiones, correcciones)
         data/01_raw/Excluidas_leche.xlsx      (plantilla base M11 — solo lectura)
         data/01_raw/LECHE_CRUDA_EST_BASE.xlsx (plantilla base M11 — solo lectura)

         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  M1 · PREPARACIÓN                                                           │
│                                                                             │
│  preparation →  Renombra la hoja activa del Excel al nombre del mes        │
│              →  Guarda BASE{PERI}_ok.xlsx en data/01_raw/                  │
│              →  Persiste cabeceras de referencia y valida semanas           │
│                                                                             │
│  Salida: data/01_raw/BASE{PERI}_ok.xlsx                                    │
│          data/01_raw/cabeceras_{PERI}.csv · semanas_{PERI}.csv             │
└─────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  M2 · INGESTA Y LIMPIEZA                                                   │
│                                                                             │
│  ingestion  →  Lectura BASE{PERI}_ok.xlsx, formateo IDFINCA, correcciones  │
│  cleaning   →  Filtros de negocio (vacas > 0, precio > 0), IDFINCA_AUX    │
│                                                                             │
│  Salida: data/03_primary/BASE{PERI}_clean.parquet                          │
└─────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  M3 · COBERTURA                                                             │
│                                                                             │
│  coverage  →  Fincas activas/inactivas vs mes anterior                     │
│             →  Tabla de variación de cobertura por municipio                │
│                                                                             │
│  Salida: data/04_feature/COBERTURA_{PERI}.parquet                          │
└─────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  M4–M6 · AGREGACIONES GEOGRÁFICAS                                           │
│                                                                             │
│  farm_price        →  Precio medio, varianza y ponderación por finca        │
│  municipality_price →  Estadísticas ponderadas por municipio (media, SD,   │
│                        CV, ponderaciones nacionales y departamentales)      │
│  dept_macro_price   →  Agrega a departamento y macrorregión lechera        │
│                                                                             │
│  Salidas: FINCA_{PERI}.parquet · MUNI_{PERI}.parquet                       │
│           DEP_{PERI}.parquet · MACRO_{PERI}.parquet                         │
└─────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  M7 · VARIACIÓN MENSUAL                                                     │
│                                                                             │
│  monthly_variation →  Merge mes actual vs mes anterior                      │
│                    →  VPRE = (precio_act - precio_ant) / precio_ant         │
│                    →  VPROD = (prod_act - prod_ant) / prod_ant              │
│                    →  TENDENCIA_PRECIO (xxx / xx / x / = / ↑ / ↑↑ / ↑↑↑)  │
│                                                                             │
│  Salidas: VAR_FINCA.parquet · VAR_MUNI.parquet                             │
│           VAR_DEP.parquet · VAR_MACRO.parquet · VAR_COB.parquet             │
└─────────────────────────────────────────────────────────────────────────────┘
         │
         ├──────────────────────────────────────────────────────────────────┐
         ▼                                                                  ▼
┌─────────────────────┐                                  ┌──────────────────────────┐
│  M8 · CORRELACIÓN   │                                  │  M9 · PANEL TRIMESTRAL   │
│                     │                                  │                          │
│  correlation →      │                                  │  panel →                 │
│  Pearson precio     │                                  │  Integra el panel base   │
│  vs producción      │                                  │  con el mes actual       │
│  por macrorregión   │                                  │  (ajuste N1/D1/N2/D2)   │
│                     │                                  │                          │
│  Salida:            │                                  │  Salida:                 │
│  CORRELACION.parquet│                                  │  PANEL_{ACT}.parquet     │
└─────────────────────┘                                  └──────────────────────────┘
         │                                                          │
         └──────────────────────┬───────────────────────────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  M10 · CUADROS DE SALIDA                                                    │
│                                                                             │
│  outputs →  Selección de columnas según tipo de entrega                     │
│          →  Escritura Excel con pandas                                      │
│          →  Formato de publicación con openpyxl (2 filas encabezado,       │
│             celdas combinadas, FINCA oculta, anchos de columna)             │
│                                                                             │
│  Salidas: data/08_reporting/                                                │
│    CUADROS_{PERI}.xlsx        — Publicación (4 hojas, FINCA oculta)        │
│    CUADROS_{PERI}_TOT.xlsx    — Análisis interno (4 hojas completas)       │
│    COBERTURA.xlsx             — Variación de cobertura (1 hoja)             │
└─────────────────────────────────────────────────────────────────────────────┘
         │
         ▼  (pipeline independiente: kedro run --pipeline cuentas_nacionales)
┌─────────────────────────────────────────────────────────────────────────────┐
│  M11 · CUENTAS NACIONALES (DSCN)                                            │
│                                                                             │
│  cuentas_nacionales                                                         │
│    calcular_semanas_operativo →  n_semanas desde semanas_validacion         │
│    calcular_excluidas         →  Actualiza Excluidas_leche_{PERI}.xlsx      │
│                                  (col. producción, total, variación,        │
│                                   fila 37 con total para la resta en D)     │
│    generar_leche_cruda        →  Actualiza LECHE_CRUDA_{PERI}.xlsx          │
│                                  D=total_macro−total_excluidas (fórmula)    │
│                                  E,F,G,H,J: fórmulas Excel                 │
│                                  LecheDANE D: ='LECHE CRUDA'!F{fila}       │
│                                  trimes D: =SUM(LecheDANE!D{ini}:D{fin})   │
│                                                                             │
│  Salidas: data/08_reporting/                                                │
│    Excluidas_leche_{PERI}.xlsx   — Panel de fincas atípicas actualizado     │
│    LECHE_CRUDA_{PERI}.xlsx       — Serie histórica con fila del mes         │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Formato de archivos intermedios

| Capa | Formato | Ubicación | Razón |
|---|---|---|---|
| Raw | `.xlsx` | `data/01_raw/` | Archivo de campo original sin modificar |
| Primary | `.parquet` | `data/03_primary/` | Datos limpios, tipados, listos para análisis |
| Feature | `.parquet` | `data/04_feature/` | Tablas procesadas por etapa geográfica |
| Reporting | `.xlsx` | `data/08_reporting/` | Entrega final con formato de publicación |

> El formato Parquet garantiza tipado estricto y lectura eficiente. No se usa CSV
> para evitar pérdida de tipos (fechas, enteros con ceros al frente).

## Panel trimestral — flujo de promoción

El panel trimestral es el insumo base para M9. Se gestiona así:

1. **Mes N-1** (mes anterior): ejecutar pipeline completo → genera `PANEL_{MES_ANT}.parquet`
2. **Cambio de mes**: ejecutar `sipsa-periodo --periodo {NUEVO}` y marcar "Promover panel"
   en la app web (o copiar manualmente `PANEL_{MES_ANT}.parquet` → `PANEL.parquet`)
3. **Mes N** (mes actual): el pipeline lee `PANEL.parquet` como insumo de M9
