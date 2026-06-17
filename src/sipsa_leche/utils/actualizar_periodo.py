"""Actualiza parameters.yml y globals.yml con los datos del nuevo período mensual.

Uso
───
    sipsa-periodo --periodo 042026
    sipsa-periodo --periodo 042026 --dry-run   # previsualiza sin modificar archivos

El código de período MMAAAA (ej. 042026 = abril 2026) es suficiente para derivar
todos los parámetros del mes: nombre, iniciales, mes anterior, nombre del archivo
Excel de entrada, etc.

Flujo de trabajo mensual
────────────────────────
    1. Colocar el Excel en data/01_raw/  (ej. BASE042026.xlsx)
    2. Ejecutar:  sipsa-periodo --periodo 042026
    3. Ejecutar:  kedro run
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import structlog

log = structlog.get_logger()

# ─── Tablas de referencia ─────────────────────────────────────────────────────

_MES_LARGO: dict[int, str] = {
    1: "ENERO",      2: "FEBRERO",   3: "MARZO",
    4: "ABRIL",      5: "MAYO",      6: "JUNIO",
    7: "JULIO",      8: "AGOSTO",    9: "SEPTIEMBRE",
    10: "OCTUBRE",   11: "NOVIEMBRE", 12: "DICIEMBRE",
}

_MES_INICIALES: dict[int, str] = {
    1: "ENE", 2: "FEB", 3: "MAR", 4: "ABR",
    5: "MAY", 6: "JUN", 7: "JUL", 8: "AGO",
    9: "SEP", 10: "OCT", 11: "NOV", 12: "DIC",
}

_MES_NOMBRE: dict[int, str] = {
    1: "enero",      2: "febrero",    3: "marzo",
    4: "abril",      5: "mayo",       6: "junio",
    7: "julio",      8: "agosto",     9: "septiembre",
    10: "octubre",   11: "noviembre", 12: "diciembre",
}


# ─── Derivación de parámetros ─────────────────────────────────────────────────

def periodo_a_params(periodo: str) -> tuple[dict[str, str], dict[str, str]]:
    """Deriva todos los parámetros de período a partir del código MMAAAA.

    Args:
        periodo: Código de seis dígitos "MMAAAA" (ej. "042026" = abril 2026).

    Returns:
        (period_params, globals_) — dicts listos para actualizar los YAML.

    Raises:
        ValueError: Si el formato del período es inválido.
    """
    if len(periodo) != 6 or not periodo.isdigit():
        raise ValueError(
            f"Período inválido: '{periodo}'. Use el formato MMAAAA (ej. 042026)."
        )

    mes  = int(periodo[:2])
    anio = int(periodo[2:])

    if not 1 <= mes <= 12:
        raise ValueError(f"Mes fuera de rango (01-12): {mes:02d}")
    if anio < 2000:
        raise ValueError(f"Año inválido: {anio}")

    # Mes anterior (manejo de cruce de año)
    mes_ant  = 12 if mes == 1 else mes - 1
    anio_ant = anio - 1 if mes == 1 else anio
    periodo_ant = f"{mes_ant:02d}{anio_ant}"

    period_params: dict[str, str] = {
        "periodo":            periodo,
        "mes_actual":         _MES_INICIALES[mes],
        "mes_anterior":       _MES_INICIALES[mes_ant],
        "mes_largo":          f"{_MES_LARGO[mes]} {anio}",
        "mes_largo_anterior": f"{_MES_LARGO[mes_ant]} {anio_ant}",
        "nombre_base":        f"BASE{periodo}",
        "mes_nombre":         _MES_NOMBRE[mes],
    }
    globals_: dict[str, str] = {
        "nombre_base": f"BASE{periodo}",
        "periodo":     periodo,
        "mes_actual":  _MES_INICIALES[mes],
        "mes_anterior": _MES_INICIALES[mes_ant],
        "mes_nombre":  _MES_NOMBRE[mes],
    }
    return period_params, globals_


# ─── Actualización de YAML (preserva comentarios con ruamel.yaml) ─────────────

def _yaml_engine() -> Any:
    from ruamel.yaml import YAML  # type: ignore[import]
    yml = YAML()
    yml.preserve_quotes = True
    yml.width = 120
    return yml


def update_parameters_yml(params_path: Path, period_params: dict[str, str]) -> None:
    """Actualiza solo las variables de período; preserva idfinca_corrections,
    macroregiones, umbrales y todos los demás parámetros estáticos."""
    yml = _yaml_engine()
    with params_path.open("r", encoding="utf-8") as f:
        data = yml.load(f)
    for key, value in period_params.items():
        if key in data:
            data[key] = value
    with params_path.open("w", encoding="utf-8") as f:
        yml.dump(data, f)
    log.info("parameters_yml_actualizado", keys=list(period_params))


def update_globals_yml(globals_path: Path, globals_: dict[str, str]) -> None:
    """Actualiza globals.yml preservando comentarios."""
    yml = _yaml_engine()
    with globals_path.open("r", encoding="utf-8") as f:
        data = yml.load(f)
    for key, value in globals_.items():
        if key in data:
            data[key] = value
    with globals_path.open("w", encoding="utf-8") as f:
        yml.dump(data, f)
    log.info("globals_yml_actualizado", keys=list(globals_))


# ─── Función principal ────────────────────────────────────────────────────────

def actualizar_periodo(
    periodo: str,
    project_root: Path | None = None,
) -> dict[str, str]:
    """Deriva los parámetros del período y actualiza parameters.yml + globals.yml.

    Args:
        periodo:      Código MMAAAA (ej. "042026").
        project_root: Raíz del proyecto Kedro; por defecto Path.cwd().

    Returns:
        period_params — dict con los 7 parámetros actualizados.
    """
    if project_root is None:
        project_root = Path.cwd()

    params_path  = project_root / "conf" / "base" / "parameters.yml"
    globals_path = project_root / "conf" / "base" / "globals.yml"

    for p in (params_path, globals_path):
        if not p.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {p}")

    period_params, globals_ = periodo_a_params(periodo)
    update_parameters_yml(params_path, period_params)
    update_globals_yml(globals_path, globals_)
    return period_params


# ─── CLI ──────────────────────────────────────────────────────────────────────

def cli() -> None:
    """Entry point: sipsa-periodo --periodo MMAAAA [--dry-run]"""
    parser = argparse.ArgumentParser(
        prog="sipsa-periodo",
        description=(
            "Actualiza parameters.yml y globals.yml para el nuevo mes.\n\n"
            "Flujo mensual:\n"
            "  1. Colocar Excel en data/01_raw/  (ej. BASE042026.xlsx)\n"
            "  2. sipsa-periodo --periodo 042026\n"
            "  3. kedro run"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--periodo",
        required=True,
        metavar="MMAAAA",
        help="Código del período a procesar, ej. 042026 para abril 2026",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=None,
        metavar="DIR",
        help="Raíz del proyecto Kedro (por defecto: directorio actual)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Muestra los parámetros que se actualizarían sin modificar archivos",
    )
    args = parser.parse_args()

    try:
        period_params, _ = periodo_a_params(args.periodo)
        _print_resumen(args.periodo, period_params, dry_run=args.dry_run)

        if not args.dry_run:
            actualizar_periodo(args.periodo, args.project_root)

    except (FileNotFoundError, ValueError) as exc:
        print(f"\nError: {exc}", file=sys.stderr)
        sys.exit(1)


def _print_resumen(
    periodo: str,
    params: dict[str, str],
    dry_run: bool = False,
) -> None:
    sufijo = " [DRY-RUN — sin cambios]" if dry_run else ""
    print(f"\n=== Parámetros para período {periodo}{sufijo} ===")
    print(f"  periodo            : {params['periodo']}")
    print(f"  nombre_base        : {params['nombre_base']}")
    print(f"  mes_actual         : {params['mes_actual']}")
    print(f"  mes_anterior       : {params['mes_anterior']}")
    print(f"  mes_largo          : {params['mes_largo']}")
    print(f"  mes_largo_anterior : {params['mes_largo_anterior']}")
    print(f"  mes_nombre         : {params['mes_nombre']}")
    if not dry_run:
        print("\n  Archivos actualizados:")
        print("    conf/base/parameters.yml")
        print("    conf/base/globals.yml")
        print("\n  Siguiente paso:  kedro run")
    print()


if __name__ == "__main__":
    cli()
