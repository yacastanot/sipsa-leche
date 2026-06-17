# 02 · Instalación

## Requisitos del sistema

- Python 3.10 o superior
- Windows 10 Pro / Windows Server 2019+
- Acceso de red a `\\DIMPE-D-065\DIMPE\SIPSA\LECHE\` (solo para panel trimestral)
- Git (para control de versiones)

## Paso a paso

### 1. Clonar el repositorio

```bash
git clone <url-codeversion>
cd sipsa-leche
```

### 2. Crear el ambiente virtual

```bash
python -m venv .venv
.venv\Scripts\activate
```

> El ambiente virtual aísla las dependencias del proyecto del Python del sistema.
> Activarlo es necesario cada vez que se abre una nueva terminal.

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
pip install -e .
```

El flag `-e .` instala el paquete `sipsa_leche` en modo editable y registra los
comandos `sipsa-leche` y `sipsa-periodo` en el PATH del ambiente.

### 4. Configurar credenciales de la app web

```bash
copy .env.example .env
```

Editar `.env` si se quieren cambiar el usuario y contraseña de la app web.
El archivo `.env` **no debe subirse a Codeversion** (ya está en `.gitignore`).

### 5. Verificar la instalación

```bash
kedro info
sipsa-periodo --help
```

Si ambos comandos responden sin error, la instalación está completa.

## Primer procesamiento

```bash
# Configurar el período
sipsa-periodo --periodo 032026

# Colocar el archivo de campo
# (copiar manualmente BASE032026.xlsx a data/01_raw/)

# Ejecutar el pipeline completo
kedro run
```

Los archivos de salida quedan en `data/08_reporting/`.

## App web

Para operar desde el navegador en lugar de la terminal:

```bash
iniciar_app.bat
```

Navegar a `http://localhost:8001`. Las credenciales por defecto están en `.env`.

## Actualización de dependencias

Si se agrega una nueva librería:

```bash
pip install <libreria>==<version>
pip freeze | findstr <libreria>   # verificar versión exacta
```

Agregar la línea con versión exacta a `requirements.txt` antes de hacer commit.
