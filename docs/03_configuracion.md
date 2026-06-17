# 03 · Configuración

El proyecto tiene tres fuentes de configuración con responsabilidades distintas.

## 1. `conf/base/parameters.yml` — Parámetros del pipeline

Archivo principal. Actualizar con `sipsa-periodo --periodo MMAAAA` al inicio de
cada mes. El resto de variables solo cambia por ajuste metodológico.

### Variables de período (se actualizan mensualmente)

| Variable | Tipo | Ejemplo | Descripción |
|---|---|---|---|
| `periodo` | str | `"032026"` | Código MMAAAA del mes actual |
| `mes_actual` | str | `"MAR"` | Iniciales del mes actual (sufijo en tablas) |
| `mes_anterior` | str | `"FEB"` | Iniciales del mes anterior |
| `mes_largo` | str | `"MARZO 2026"` | Nombre completo para rutas de carpetas |
| `mes_largo_anterior` | str | `"FEBRERO 2026"` | Nombre completo del mes anterior |
| `nombre_base` | str | `"BASE032026"` | Nombre del Excel de entrada (sin .xlsx) |
| `mes_nombre` | str | `"marzo"` | Nombre en minúsculas para hoja `_ok.xlsx` |

### Panel trimestral (`panel_ajuste`)

Factor de ajuste para meses incompletos del operativo. En condiciones normales
los cuatro valores permanecen en el neutro (N=0, D=1).

| Variable | Tipo | Valor neutro | Descripción |
|---|---|---|---|
| `panel_ajuste.N1` | float | `0` | Numerador del ajuste del mes anterior |
| `panel_ajuste.D1` | float | `1` | Denominador del ajuste del mes anterior |
| `panel_ajuste.N2` | float | `0` | Numerador del ajuste del mes actual |
| `panel_ajuste.D2` | float | `1` | Denominador del ajuste del mes actual |

> Fórmula: `T_PROD2 = T_PROD × (1 + N/D)`. Con N=0 y D=1: `T_PROD2 = T_PROD`.

### Umbrales de tendencia del precio

Definen los cortes para clasificar la variación en 7 categorías (xxx a ↑↑↑).
Finca/Municipio usa ±5% como estable; Depto/Macro usa ±3% (más estricto).

| Grupo | Variable | Valor por defecto |
|---|---|---|
| `tendencia_umbral_finca_muni` | `bajo_extremo` | `-0.12` |
| | `bajo_fuerte` | `-0.07` |
| | `bajo_leve` | `-0.05` |
| | `estable_sup` | `0.05` |
| | `alto_leve` | `0.07` |
| | `alto_fuerte` | `0.12` |
| `tendencia_umbral_dep_macro` | `bajo_leve` | `-0.03` |
| | `estable_sup` | `0.03` |
| | (resto igual) | — |

### Otras variables estables

| Variable | Descripción |
|---|---|
| `servidor_dimpe` | Ruta UNC al servidor DIMPE-D-065 |
| `ruta_panel` | Ruta UNC a la carpeta del panel trimestral |
| `idfinca_corrections` | Lista de 14 correcciones de IDFINCA mal registradas |
| `macroregiones` | Mapeo departamento (COD_DEP) → macrorregión lechera |
| `regresion_tolerancia` | Diferencia máxima aceptable en tests de regresión (0.0001) |

### Rutas Cuentas Nacionales — M11

Rutas a los archivos base en OneDrive que M11 usa como plantilla de solo lectura.
El pipeline **no modifica estos archivos**; genera copias del período en `data/08_reporting/`.

| Variable | Descripción |
|---|---|
| `ruta_excluidas` | Ruta absoluta a `Excluidas_leche.xlsx` (OneDrive) |
| `ruta_leche_cruda_base` | Ruta absoluta a `LECHE_CRUDA_EST_BASE.xlsx` (OneDrive) |

Ejemplo en `parameters.yml`:

```yaml
ruta_excluidas: "C:/Users/Jeferson/OneDrive - Cloud Integration Hub/Documentos/DANE
  Automatización/SIPSA Leche/Excluidas_leche.xlsx"
ruta_leche_cruda_base: "C:/Users/Jeferson/OneDrive - Cloud Integration Hub/Documentos/DANE
  Automatización/SIPSA Leche/LECHE_CRUDA_EST_BASE.xlsx"
```

> Estas rutas son específicas de la máquina del analista. Actualizar si la carpeta
> de OneDrive está en una ruta distinta.

---

## 2. `conf/base/globals.yml` — Variables globales del catálogo

Subconjunto de `parameters.yml` utilizado por `catalog.yml` para nombrar
los archivos del catálogo Kedro (`${globals:nombre_base}`, etc.).
**Se actualiza automáticamente junto con `parameters.yml`** al ejecutar
`sipsa-periodo`.

| Variable | Descripción |
|---|---|
| `nombre_base` | Nombre del archivo fuente sin extensión |
| `periodo` | Código MMAAAA |
| `mes_actual` | Iniciales mes actual |
| `mes_anterior` | Iniciales mes anterior |
| `mes_nombre` | Nombre del mes en minúsculas |

---

## 3. `.env` — Credenciales de la app web

Nunca subir a Codeversion. Copiar desde `.env.example` y editar localmente.

| Variable | Por defecto | Descripción |
|---|---|---|
| `LECHE_USER` | `sipsa` | Usuario para autenticación HTTP Basic |
| `LECHE_PASS` | `cambiar_esta_clave` | Contraseña de la app web |

La app lee estas variables al iniciar. Cambiarlas requiere reiniciar `uvicorn`.
