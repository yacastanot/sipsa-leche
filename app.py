"""FastAPI web app para ejecutar el pipeline SIPSA Leche.

Equivalente funcional a la app del SIPSA precios, adaptada al proceso mensual:
  - Carga del archivo BASE{MMYYYY}.xlsx
  - Configuración del período (mes_actual, mes_anterior, periodo, nombre_base)
  - Promoción del panel trimestral al nuevo período
  - Ejecución de pipelines individuales o el completo (M2–M10)
  - Streaming de logs vía Server-Sent Events
  - Descarga de los XLSX de salida

Credenciales: variables de entorno LECHE_USER / LECHE_PASS
  (por defecto: sipsa / cambiar_esta_clave)
"""
from __future__ import annotations

import asyncio
import os
import queue
import re
import secrets
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, Response, StreamingResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from ruamel.yaml import YAML as _YAML

# ── Rutas del proyecto ────────────────────────────────────────────────────────

PROJECT_ROOT  = Path(__file__).parent
RAW_DIR       = PROJECT_ROOT / "data" / "01_raw"
PRIMARY_DIR   = PROJECT_ROOT / "data" / "03_primary"
FEATURE_DIR   = PROJECT_ROOT / "data" / "04_feature"
REPORTING_DIR = PROJECT_ROOT / "data" / "08_reporting"
GLOBALS_YML   = PROJECT_ROOT / "conf" / "base" / "globals.yml"
PARAMS_YML    = PROJECT_ROOT / "conf" / "base" / "parameters.yml"

# ── Catálogos de dominio ──────────────────────────────────────────────────────

MESES: dict[int, tuple[str, str]] = {
    1:  ("ENE", "ENERO"),       2:  ("FEB", "FEBRERO"),
    3:  ("MAR", "MARZO"),       4:  ("ABR", "ABRIL"),
    5:  ("MAY", "MAYO"),        6:  ("JUN", "JUNIO"),
    7:  ("JUL", "JULIO"),       8:  ("AGO", "AGOSTO"),
    9:  ("SEP", "SEPTIEMBRE"),  10: ("OCT", "OCTUBRE"),
    11: ("NOV", "NOVIEMBRE"),   12: ("DIC", "DICIEMBRE"),
}

PIPELINES: list[tuple[str, str]] = [
    ("__default__",  "Completo — M2 a M10"),
    ("silver",       "Silver — Raw → Municipio (M2–M6)"),
    ("gold_outputs", "Gold — Variación → Salidas (M7–M10)"),
    ("ingestion",    "M2 · Ingesta Excel"),
    ("cleaning",     "M2 · Depuración y reglas de negocio"),
    ("coverage",     "M3 · Cobertura y excluidas"),
    ("farm_price",   "M4 · Precio medio por finca"),
    ("muni_price",   "M5 · Precio medio por municipio"),
    ("dept_macro",   "M6 · Precio por depto y macrorregión"),
    ("variation",    "M7 · Variación mensual + TENDENCIA"),
    ("correlation",  "M8 · Correlación precio vs producción"),
    ("panel",        "M9 · Panel trimestral"),
    ("outputs",      "M10 · Cuadros Excel de publicación"),
]

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(title="SIPSA Leche Pipeline", docs_url=None, redoc_url=None)
templates = Jinja2Templates(directory=str(PROJECT_ROOT / "templates"))
security = HTTPBasic()

_pipeline_running = False


# ── Autenticación ─────────────────────────────────────────────────────────────

def _check_auth(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    expected_user = os.environ.get("LECHE_USER", "sipsa")
    expected_pass = os.environ.get("LECHE_PASS", "cambiar_esta_clave")
    user_ok = secrets.compare_digest(credentials.username.encode(), expected_user.encode())
    pass_ok = secrets.compare_digest(credentials.password.encode(), expected_pass.encode())
    if not (user_ok and pass_ok):
        raise HTTPException(
            status_code=401,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


# ── Helpers YAML ──────────────────────────────────────────────────────────────

def _set_yaml_value(text: str, key: str, value: str) -> str:
    """Reemplaza `key: "valor"` preservando alineación y comentarios de la línea."""
    pattern = rf'^({re.escape(key)}:\s*)"[^"]*"'
    replacement = rf'\1"{value}"'
    return re.sub(pattern, replacement, text, flags=re.MULTILINE)


def _read_globals() -> dict[str, str]:
    """Lee globals.yml y devuelve los pares clave-valor como diccionario."""
    text = GLOBALS_YML.read_text(encoding="utf-8")
    result: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        m = re.match(r'^(\w+):\s*"([^"]*)"', stripped)
        if m:
            result[m.group(1)] = m.group(2)
    return result


def _write_globals(nombre_base: str, periodo: str, mes_actual: str, mes_anterior: str) -> None:
    text = GLOBALS_YML.read_text(encoding="utf-8")
    for key, val in [
        ("nombre_base", nombre_base),
        ("periodo",     periodo),
        ("mes_actual",  mes_actual),
        ("mes_anterior", mes_anterior),
    ]:
        text = _set_yaml_value(text, key, val)
    GLOBALS_YML.write_text(text, encoding="utf-8")


def _write_parameters(
    nombre_base: str, periodo: str, mes_actual: str, mes_anterior: str,
    mes_largo: str, mes_largo_anterior: str,
) -> None:
    text = PARAMS_YML.read_text(encoding="utf-8")
    for key, val in [
        ("periodo",             periodo),
        ("mes_actual",          mes_actual),
        ("mes_anterior",        mes_anterior),
        ("mes_largo",           mes_largo),
        ("mes_largo_anterior",  mes_largo_anterior),
        ("nombre_base",         nombre_base),
    ]:
        text = _set_yaml_value(text, key, val)
    PARAMS_YML.write_text(text, encoding="utf-8")


# ── Modelos ───────────────────────────────────────────────────────────────────

class ConfigRequest(BaseModel):
    mes_num: int
    anio: int
    promover_panel: bool = False


class ConfigAdvanced(BaseModel):
    panel_N1: float = 0.0
    panel_D1: float = 1.0
    panel_N2: float = 0.0
    panel_D2: float = 1.0
    finca_bajo_extremo: float = -0.12
    finca_bajo_fuerte:  float = -0.07
    finca_bajo_leve:    float = -0.05
    finca_estable_sup:  float =  0.05
    finca_alto_leve:    float =  0.07
    finca_alto_fuerte:  float =  0.12
    dep_bajo_extremo: float = -0.12
    dep_bajo_fuerte:  float = -0.07
    dep_bajo_leve:    float = -0.03
    dep_estable_sup:  float =  0.03
    dep_alto_leve:    float =  0.07
    dep_alto_fuerte:  float =  0.12


# ── Helpers parámetros avanzados ──────────────────────────────────────────────

def _read_advanced_params() -> dict:
    """Lee panel_ajuste y umbrales de tendencia desde parameters.yml."""
    yml = _YAML()
    with PARAMS_YML.open("r", encoding="utf-8") as f:
        data = yml.load(f)
    pa = data.get("panel_ajuste", {})
    fm = data.get("tendencia_umbral_finca_muni", {})
    dm = data.get("tendencia_umbral_dep_macro", {})
    return {
        "panel_N1": float(pa.get("N1", 0)),
        "panel_D1": float(pa.get("D1", 1)),
        "panel_N2": float(pa.get("N2", 0)),
        "panel_D2": float(pa.get("D2", 1)),
        "finca_bajo_extremo": float(fm.get("bajo_extremo", -0.12)),
        "finca_bajo_fuerte":  float(fm.get("bajo_fuerte",  -0.07)),
        "finca_bajo_leve":    float(fm.get("bajo_leve",    -0.05)),
        "finca_estable_sup":  float(fm.get("estable_sup",   0.05)),
        "finca_alto_leve":    float(fm.get("alto_leve",     0.07)),
        "finca_alto_fuerte":  float(fm.get("alto_fuerte",   0.12)),
        "dep_bajo_extremo": float(dm.get("bajo_extremo", -0.12)),
        "dep_bajo_fuerte":  float(dm.get("bajo_fuerte",  -0.07)),
        "dep_bajo_leve":    float(dm.get("bajo_leve",    -0.03)),
        "dep_estable_sup":  float(dm.get("estable_sup",   0.03)),
        "dep_alto_leve":    float(dm.get("alto_leve",     0.07)),
        "dep_alto_fuerte":  float(dm.get("alto_fuerte",   0.12)),
    }


def _write_advanced_params(body: ConfigAdvanced) -> None:
    """Actualiza panel_ajuste y umbrales en parameters.yml preservando comentarios."""
    yml = _YAML()
    yml.preserve_quotes = True
    with PARAMS_YML.open("r", encoding="utf-8") as f:
        data = yml.load(f)

    pa = data["panel_ajuste"]
    pa["N1"] = body.panel_N1
    pa["D1"] = body.panel_D1
    pa["N2"] = body.panel_N2
    pa["D2"] = body.panel_D2

    fm = data["tendencia_umbral_finca_muni"]
    fm["bajo_extremo"] = body.finca_bajo_extremo
    fm["bajo_fuerte"]  = body.finca_bajo_fuerte
    fm["bajo_leve"]    = body.finca_bajo_leve
    fm["estable_sup"]  = body.finca_estable_sup
    fm["alto_leve"]    = body.finca_alto_leve
    fm["alto_fuerte"]  = body.finca_alto_fuerte

    dm = data["tendencia_umbral_dep_macro"]
    dm["bajo_extremo"] = body.dep_bajo_extremo
    dm["bajo_fuerte"]  = body.dep_bajo_fuerte
    dm["bajo_leve"]    = body.dep_bajo_leve
    dm["estable_sup"]  = body.dep_estable_sup
    dm["alto_leve"]    = body.dep_alto_leve
    dm["alto_fuerte"]  = body.dep_alto_fuerte

    with PARAMS_YML.open("w", encoding="utf-8") as f:
        yml.dump(data, f)


# ── Rutas ─────────────────────────────────────────────────────────────────────

@app.get("/favicon.ico", include_in_schema=False)
async def favicon() -> Response:
    return Response(status_code=204)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, _: str = Depends(_check_auth)) -> HTMLResponse:
    config = _read_globals()
    periodo = config.get("periodo", "012026")
    try:
        mes_num = int(periodo[:2])
        anio    = int(periodo[2:])
    except ValueError:
        mes_num, anio = 1, 2026
    return templates.TemplateResponse(request, "index.html", {
        "config":    config,
        "mes_num":   mes_num,
        "anio":      anio,
        "pipelines": PIPELINES,
    })


@app.get("/config")
async def get_config(_: str = Depends(_check_auth)) -> dict:
    return _read_globals()


@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    _: str = Depends(_check_auth),
) -> dict:
    if not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(400, "Solo se aceptan archivos Excel (.xlsx, .xls)")
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    dest = RAW_DIR / file.filename
    contents = await file.read()
    dest.write_bytes(contents)
    return {"filename": file.filename, "size_kb": round(len(contents) / 1024, 1)}


@app.post("/configure")
async def configure(
    body: ConfigRequest,
    _: str = Depends(_check_auth),
) -> dict:
    """Actualiza globals.yml y parameters.yml con los nuevos valores de período."""
    mes_num = body.mes_num
    anio    = body.anio

    if not (1 <= mes_num <= 12):
        raise HTTPException(400, "mes_num debe estar entre 1 y 12")
    if not (2020 <= anio <= 2040):
        raise HTTPException(400, "Año fuera del rango permitido (2020–2040)")

    mes_ant_num = 12 if mes_num == 1 else mes_num - 1
    anio_ant    = anio - 1 if mes_num == 1 else anio

    abr_act, largo_act = MESES[mes_num]
    abr_ant, largo_ant = MESES[mes_ant_num]

    periodo           = f"{mes_num:02d}{anio}"
    nombre_base       = f"BASE{periodo}"
    mes_largo         = f"{largo_act} {anio}"
    mes_largo_anterior = f"{largo_ant} {anio_ant}"

    old_cfg    = _read_globals()
    old_peri   = old_cfg.get("periodo", "")
    old_mes    = old_cfg.get("mes_actual", "")

    if body.promover_panel:
        panel_src = FEATURE_DIR / f"PANEL_{old_mes}.parquet"
        panel_dst = PRIMARY_DIR / "PANEL.parquet"
        if not panel_src.exists():
            raise HTTPException(
                404,
                f"Panel del mes anterior no encontrado: {panel_src.name}. "
                "Ejecuta primero el pipeline Panel trimestral para el mes actual.",
            )
        shutil.copy2(str(panel_src), str(panel_dst))

    _write_globals(nombre_base, periodo, abr_act, abr_ant)
    _write_parameters(nombre_base, periodo, abr_act, abr_ant, mes_largo, mes_largo_anterior)

    return {
        "ok":                True,
        "periodo":           periodo,
        "mes_actual":        abr_act,
        "mes_anterior":      abr_ant,
        "nombre_base":       nombre_base,
        "mes_largo":         mes_largo,
        "mes_largo_anterior": mes_largo_anterior,
        "panel_promovido":   body.promover_panel,
    }


@app.get("/config/advanced")
async def get_advanced_config(_: str = Depends(_check_auth)) -> dict:
    return _read_advanced_params()


@app.post("/configure/advanced")
async def configure_advanced(
    body: ConfigAdvanced,
    _: str = Depends(_check_auth),
) -> dict:
    """Actualiza panel_ajuste y umbrales de tendencia en parameters.yml."""
    _write_advanced_params(body)
    return {"ok": True, **body.model_dump()}


@app.get("/status")
async def status(_: str = Depends(_check_auth)) -> dict:
    return {"running": _pipeline_running}


@app.get("/outputs")
async def list_outputs(_: str = Depends(_check_auth)) -> dict:
    if not REPORTING_DIR.exists():
        return {"files": []}
    files = sorted(
        REPORTING_DIR.glob("*.xlsx"),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )
    return {"files": [f.name for f in files]}


@app.delete("/outputs")
async def clear_outputs(_: str = Depends(_check_auth)) -> dict:
    if not REPORTING_DIR.exists():
        return {"deleted": 0, "protected": 0}
    deleted = 0
    protected = 0
    for f in REPORTING_DIR.glob("*.xlsx"):
        if f.name.startswith("LECHE_CRUDA_") or f.name.startswith("Excluidas_leche_"):
            protected += 1
            continue
        f.unlink()
        deleted += 1
    return {"deleted": deleted, "protected": protected}


@app.get("/download/{filename}")
async def download(filename: str, _: str = Depends(_check_auth)) -> FileResponse:
    path = (REPORTING_DIR / filename).resolve()
    if not str(path).startswith(str(REPORTING_DIR.resolve())):
        raise HTTPException(403, "Acceso denegado")
    if not path.exists():
        raise HTTPException(404, "Archivo no encontrado")
    return FileResponse(
        str(path),
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.post("/run")
async def run_pipeline(
    pipeline_name: str = Form("__default__"),
    _: str = Depends(_check_auth),
) -> StreamingResponse:
    global _pipeline_running
    if _pipeline_running:
        raise HTTPException(409, "El pipeline ya está en ejecución")

    cmd = [sys.executable, "-m", "kedro", "run"]
    if pipeline_name != "__default__":
        cmd += ["--pipeline", pipeline_name]

    line_queue: queue.Queue = queue.Queue()

    def _run_kedro() -> None:
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(PROJECT_ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            for line in proc.stdout:
                line_queue.put(line.rstrip())
            proc.wait()
            line_queue.put(("__DONE__", proc.returncode))
        except Exception as exc:
            line_queue.put(("__DONE__", str(exc)))

    async def generate():
        global _pipeline_running
        _pipeline_running = True
        thread = threading.Thread(target=_run_kedro, daemon=True)
        thread.start()
        loop = asyncio.get_event_loop()
        try:
            while True:
                item = await loop.run_in_executor(None, line_queue.get)
                if isinstance(item, tuple) and item[0] == "__DONE__":
                    rc = item[1]
                    if rc == 0:
                        yield "data: __SUCCESS__\n\n"
                    else:
                        yield f"data: __ERROR__{rc}\n\n"
                    break
                yield f"data: {item}\n\n"
        except Exception as exc:
            yield f"data: __ERROR__{exc}\n\n"
        finally:
            _pipeline_running = False

    return StreamingResponse(generate(), media_type="text/event-stream")
