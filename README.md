# SIPSA Leche — Pipeline mensual de precios

Pipeline de automatización del operativo mensual de precios al productor de leche cruda
del sistema SIPSA (DANE). Procesa el archivo de campo `BASE{MMYYYY}.xlsx` y produce
cuadros de variación, tendencia y cobertura listos para publicación.

## Inicio rápido

```bash
# 1. Clonar y activar ambiente
git clone <url-del-repositorio>
cd sipsa-leche
python -m venv .venv
.venv\Scripts\activate          # Windows

# 2. Instalar dependencias
pip install -r requirements.txt
pip install -e .

# 3. Configurar credenciales de la app web
copy .env.example .env          # editar si se cambian usuario/contraseña

# 4. Configurar el mes a procesar
sipsa-periodo --periodo 042026  # reemplazar con el período real

# 5. Colocar el Excel de campo en data/01_raw/
#    Ejemplo: data/01_raw/BASE042026.xlsx

# 6. Ejecutar el pipeline
kedro run
```

## Requisitos

| Componente | Versión mínima |
|---|---|
| Python | 3.10+ |
| Kedro | 0.19.15 |
| Sistema operativo | Windows 10 / Windows Server 2019+ |
| Servidor DIMPE | Acceso a `\\DIMPE-D-065\DIMPE\SIPSA\LECHE\` |

## App web (opcional)

Para ejecutar el pipeline desde el navegador sin usar la terminal:

```bash
iniciar_app.bat   # abre http://localhost:8001
```

Usuario por defecto: `sipsa` | Contraseña: `cambiar_esta_clave`

## Estado del proyecto

**Estable** — En producción desde el período 032026.

## Documentación completa

| Archivo | Contenido |
|---|---|
| [docs/01_arquitectura.md](docs/01_arquitectura.md) | Decisiones de diseño y diagrama de componentes |
| [docs/02_instalacion.md](docs/02_instalacion.md) | Setup detallado paso a paso |
| [docs/03_configuracion.md](docs/03_configuracion.md) | Todas las variables de configuración |
| [docs/04_modulos.md](docs/04_modulos.md) | Qué hace cada archivo de `src/` y `utils/` |
| [docs/05_flujo_datos.md](docs/05_flujo_datos.md) | Flujo de datos de extremo a extremo |
| [docs/06_git.md](docs/06_git.md) | Convenciones de ramas, commits y PRs |
