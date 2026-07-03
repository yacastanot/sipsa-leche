# 04 · Módulos

## Estructura general

```
src/sipsa_leche/
├── macro_leche.py          # Punto de entrada público del paquete
├── pipeline_registry.py    # Registro de pipelines Kedro
├── settings.py             # Configuración del proyecto Kedro
├── __main__.py             # Entry point: sipsa-leche
├── pipelines/              # Nodos agrupados por etapa (M1–M11)
│   ├── preparation/        # M1  · Preparación del Excel de campo
│   ├── ingestion/          # M2  · Ingesta y snapshot bronze
│   ├── cleaning/           # M2  · Depuración y reglas de negocio
│   ├── coverage/           # M3  · Cobertura y exclusiones
│   ├── farm_price/         # M4  · Precio medio por finca
│   ├── municipality_price/ # M5  · Precio medio por municipio
│   ├── dept_macro_price/   # M6  · Precio por depto y macrorregión
│   ├── monthly_variation/  # M7  · Variación mensual + TENDENCIA
│   ├── correlation/        # M8  · Correlación precio vs producción
│   ├── panel/              # M9  · Panel trimestral de fincas
│   ├── outputs/            # M10 · Cuadros Excel de publicación
│   └── cuentas_nacionales/ # M11 · Leche Cruda y Excluidas para DSCN
└── utils/                  # Utilidades reutilizables (sin estado)
    ├── actualizar_periodo.py
    ├── excel_format.py
    ├── idfinca.py
    ├── macroregion.py
    ├── tendencia.py
    └── weighted_stats.py
```

---

## Pipelines (`src/sipsa_leche/pipelines/`)

Cada carpeta de pipeline contiene `nodes.py` (funciones puras) y `pipeline.py`
(definición del grafo Kedro con entradas/salidas del catálogo).

| Pipeline | Etapa SAS equivalente | Descripción |
|---|---|---|
| `preparation` | M1 (nuevo) | Renombra hoja del Excel de campo al mes, persiste encabezados de referencia, valida semanas |
| `ingestion` | Lectura Excel inicial | Lee `BASE{PERI}_ok.xlsx`, formatea IDFINCA, aplica correcciones |
| `cleaning` | Reglas de negocio | Filtra registros inválidos, calcula IDFINCA_AUX |
| `coverage` | `%COBERTURA` | Identifica fincas activas/inactivas, genera variación de cobertura |
| `farm_price` | `%FINCA` | Precio medio, varianza y ponderación por finca |
| `municipality_price` | `%MUNICIPIO` | Estadísticas ponderadas por municipio |
| `dept_macro_price` | `%DEPTO` / `%MACRO` | Agrega a departamento y macrorregión lechera |
| `monthly_variation` | `%VARIACION` | Variación mensual precio y producción + TENDENCIA_PRECIO |
| `correlation` | M8 | Correlación Pearson precio vs producción |
| `panel` | `%PANEL` | Panel trimestral de fincas con ajuste N1/D1/N2/D2 |
| `outputs` | `%CONSULTA` + `%EXPORT` | Cuadros Excel TOT, pub y COBERTURA |
| `cuentas_nacionales` | M11 (nuevo) | Genera `LECHE_CRUDA_{PERI}.xlsx` y `Excluidas_leche_{PERI}.xlsx` para DSCN |

### M11 · `cuentas_nacionales` — detalle

Requiere que M7 haya corrido (consume `variacion_finca` y `variacion_macro`).
Produce dos archivos en `data/08_reporting/`:

**`Excluidas_leche_{PERI}.xlsx`** — copia actualizada del panel de fincas atípicas:
- Hoja1: nueva columna `PRODC{MM}{YYYY}` con producción de cada finca excluida
  (cruzada desde `variacion_finca`), total, variación (fórmula), salen, entran, diferencia.
- Hoja2: dump completo del panel (IDFINCA, T_PROD_ant, T_PROD_act) para referencia.

**`LECHE_CRUDA_{PERI}.xlsx`** — copia del histórico con la fila del mes calculada:

| Hoja | Celda | Fórmula / Valor |
|---|---|---|
| LECHE CRUDA | D | `=total_macro-total_excluidas` |
| LECHE CRUDA | E | `=dias/(7*n_semanas)` |
| LECHE CRUDA | F | `=D*E` |
| LECHE CRUDA | G | `=(F/F_anterior)-1` |
| LECHE CRUDA | H | `=((F-F_12_meses)/F_12_meses)*100` |
| LECHE CRUDA | J | `=(G+1)*J_anterior` |
| LecheDANE | D | `='LECHE CRUDA'!F{fila}` |
| LecheDANE | E | `=(D/D_anterior)-1` |
| LecheDANE | F | `=(D/D_12_meses)-1` |
| trimes | D | `=SUM(LecheDANE!D{inicio_trim}:D{fila})` |
| trimes | E | `=(D/D_trim_anterior)-1` |
| trimes | F | `=(D/D_mismo_trim_año_ant)-1` |

> `total_macro` = suma de `T_PRODUCCION_MACRO{MES}` del parquet `variacion_macro`.
> `total_excluidas` = suma de producción de las fincas en el panel de atípicas
> (fila 37 de Hoja1 de `Excluidas_leche_{PERI}.xlsx`).
> `n_semanas` = número de filas en `semanas_validacion` (conteo de semanas del operativo).

---

## Utilidades (`src/sipsa_leche/utils/`)

### `actualizar_periodo.py`

Herramienta CLI para actualizar los parámetros de período sin editar YAML manualmente.

```bash
# Uso típico al inicio del mes
sipsa-periodo --periodo 042026

# Ver qué se actualizaría sin modificar archivos
sipsa-periodo --periodo 042026 --dry-run
```

Funciones públicas:
- `periodo_a_params(periodo)` — Deriva los 7 parámetros del código MMAAAA
- `actualizar_periodo(periodo, project_root)` — Escribe `parameters.yml` y `globals.yml`

### `excel_format.py`

Aplica formato de publicación a los Excel generados por pandas (post-proceso con openpyxl).

Funciones públicas:
- `formatear_cuadros_pub(path, ant, act)` — Encabezados en 2 filas, FINCA oculta, anchos
- `formatear_cuadros_tot(path)` — Encabezados sin negrita, anchos de columna

Llamadas automáticamente desde el nodo `generar_cuadros_salida` (pipeline `outputs`).

### `idfinca.py`

Manejo del identificador único de finca (formato 7 dígitos, notación científica de Excel).

Funciones públicas:
- `format_idfinca(raw_val)` — Convierte a string de 7 dígitos con ceros a la izquierda
- `apply_idfinca_corrections(df, corrections)` — Aplica las 14 correcciones de `parameters.yml`

### `macroregion.py`

Asignación de macrorregión lechera a partir del código de departamento.

Funciones públicas:
- `assign_macroregion(df, macroregiones)` — Mapea `COD_DEP` → `MACRO` usando el dict de parámetros

### `tendencia.py`

Clasificación de tendencia del precio en 7 niveles (xxx a °°°).

Funciones públicas:
- `classify_tendency(variacion, umbrales)` — Clasifica un valor escalar
- `apply_tendency_column(df, variacion_col, umbrales, output_col)` — Aplica vectorialmente

### `weighted_stats.py`

Estadísticas ponderadas por producción (equivalente exacto a las macros SAS).

> La varianza usada es ponderada, no muestral. `pandas.std(ddof=1)` NO es equivalente.

Funciones públicas:
- `weighted_mean(values, weights)` — Media ponderada Σ(v×w)/Σ(w)
- `weighted_std(values, weights)` — Desviación estándar ponderada √Σ(w×(v−μ)²)
- `weighted_var(values, weights)` — Varianza ponderada Σ(w×(v−μ)²)

---

## Punto de entrada del paquete (`macro_leche.py`)

Re-exporta todas las funciones de nodo del proyecto para uso en notebooks o scripts externos.
También contiene el flujo de trabajo mensual resumido y los comandos rápidos de Kedro.

```python
from sipsa_leche.macro_leche import calcular_precio_finca, generar_leche_cruda
```

---

## App web (`app.py`)

API FastAPI para operar el pipeline desde el navegador.

| Endpoint | Método | Descripción |
|---|---|---|
| `GET /` | — | Dashboard principal |
| `POST /upload` | — | Sube `BASE{PERI}.xlsx` a `data/01_raw/` |
| `POST /configure` | — | Actualiza período en `globals.yml` y `parameters.yml` |
| `GET /config/advanced` | — | Lee `panel_ajuste` y umbrales de tendencia |
| `POST /configure/advanced` | — | Guarda `panel_ajuste` y umbrales |
| `POST /run` | — | Ejecuta un pipeline Kedro con streaming SSE de logs |
| `GET /outputs` | — | Lista los Excel generados en `data/08_reporting/` |
| `GET /download/{filename}` | — | Descarga un archivo de resultados |
