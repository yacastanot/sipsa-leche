# 06 · Convenciones Git

## Estrategia de ramas

```
main
 └── develop              ← rama de integración
      ├── feature/...     ← nuevas funcionalidades
      ├── fix/...         ← correcciones de errores
      └── docs/...        ← documentación únicamente
```

| Rama | Propósito | Quién hace merge |
|---|---|---|
| `main` | Código en producción, estable | Solo desde `develop` vía PR aprobado |
| `develop` | Integración continua, debe pasar pruebas | Merge de `feature/`, `fix/`, `docs/` |
| `feature/nombre` | Desarrollo de una funcionalidad nueva | Merge a `develop` vía PR |
| `fix/nombre` | Corrección de un error específico | Merge a `develop` vía PR |
| `docs/nombre` | Solo cambios de documentación | Merge a `develop` vía PR |

## Nombres de rama

Formato: `tipo/descripcion-en-minusculas-con-guiones`

```bash
# Correcto
feature/umbrales-configurables
fix/idfinca-notacion-cientifica
docs/modulos-utils

# Incorrecto
Feature/NuevoModulo
fix_panel
mi-rama
```

## Mensajes de commit

Formato: `tipo: descripción breve en presente`

| Tipo | Cuándo usarlo |
|---|---|
| `feat` | Nueva funcionalidad |
| `fix` | Corrección de bug |
| `docs` | Solo documentación |
| `refactor` | Cambio de código sin nueva funcionalidad ni bug |
| `test` | Agregar o modificar tests |
| `chore` | Tareas de mantenimiento (dependencias, CI, configuración) |

```bash
# Correcto
feat: agregar umbrales configurables para tendencia dep/macro
fix: corregir cálculo de varianza ponderada en weighted_std
docs: agregar docs/05_flujo_datos.md con diagrama de pipeline
refactor: extraer lógica de formato Excel a utils/excel_format.py

# Incorrecto
actualizando codigo
fix
Agrega nueva funcionalidad de panel
```

## Checklist de un Pull Request

Un PR no está completo si no tiene todo esto:

- [ ] Código nuevo/modificado en `src/` o `utils/`
- [ ] Docstrings Google Style en toda función pública nueva o modificada
- [ ] `docs/04_modulos.md` actualizado si se agregó o cambió un módulo
- [ ] `docs/03_configuracion.md` actualizado si hay nuevas variables de configuración
- [ ] `.env.example` actualizado si se agregó una variable de entorno
- [ ] `requirements.txt` con versión exacta si se agregó una dependencia nueva
- [ ] Tests pasan: `pytest`

**Un PR sin docstrings es rechazado. Un PR sin actualización de docs es rechazado.**

## Flujo de trabajo mensual (no es un PR)

El cambio de período mensual se hace directamente sobre `develop` o `main`
(no requiere rama separada) usando:

```bash
sipsa-periodo --periodo MMAAAA
```

Este comando solo modifica `conf/base/parameters.yml` y `conf/base/globals.yml`.

## Lo que no va en el repositorio

Estos elementos están en `.gitignore` y **nunca deben subirse**:

- `data/` — Los datos del operativo son sensibles y voluminosos
- `.env` — Credenciales de la app web
- `.venv/` — El ambiente virtual se recrea desde `requirements.txt`
- `__pycache__/` y archivos `.pyc`
- Archivos `.xlsx` de salida (van en el servidor de reportes)
