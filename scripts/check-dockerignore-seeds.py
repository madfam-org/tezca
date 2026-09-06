#!/usr/bin/env python3
"""
check-dockerignore-seeds.py — CI lint: las semillas que los comandos de
publicación necesitan tienen que viajar en la imagen.

EL BUG QUE PREVIENE
===================
El 2026-09-06, en el pod `tezca-api` (imagen de #234, cwd `/app`):

    python manage.py publish_law_articles --dry-run
      → No existe el seed: data/labor/articulos_vigentes.json
    python manage.py publish_labor_rules  --dry-run
      → No se pudo leer el catálogo del SAT en data/labor/sat_catalogos.json:
        [Errno 2] ... No se escribió nada.

Los dos JSON estaban en git (los añadieron #233 y #234) y los dos comandos
fallaron **limpiamente, sin escribir a medias** — el fail-closed hizo su
trabajo. Lo que faltaba era el archivo: `.dockerignore` excluye `data/*` (el
corpus vive en Postgres + ES, no en la imagen) y re-incluye a mano sólo tres
registros. `data/labor/*.json` no estaba en esa lista, así que `COPY . .`
nunca los subió.

La clase de bug: **una semilla que un comando de publicación lee por omisión,
excluida de la imagen por `.dockerignore`**. Es invisible en CI y en local
—donde el árbol de git está completo— y sólo se manifiesta cuando un operador
entra al pod a publicar. El costo aguas abajo no es un error: es un feed
laboral vacío, y symbiosis-hcm es fail-closed contra Tezca, así que no publica
ni una obligación mientras tanto.

QUÉ VERIFICA
============
Simula las reglas de `.dockerignore` (mismo orden de precedencia que usa
BuildKit: gana el ÚLTIMO patrón que casa) sobre una lista explícita de rutas
que los comandos de publicación necesitan, y falla si alguna queda excluida.

También exige que cada ruta **exista en el árbol**: un `.dockerignore`
perfecto no sirve de nada si el archivo se borró o se renombró, y el síntoma
en el pod es idéntico.

Las rutas vigiladas se declaran en `SEMILLAS_REQUERIDAS`, cada una con el
comando que la lee. Al añadir una semilla nueva a `data/`, agrégala ahí: es
una línea, y es la diferencia entre que CI lo atrape y que lo atrape un
operador en producción.

USO
===
    python3 scripts/check-dockerignore-seeds.py
    python3 scripts/check-dockerignore-seeds.py --repo-root .

Códigos de salida:
  0 — todas las semillas viajan en la imagen
  1 — al menos una queda excluida por .dockerignore, o no existe
  2 — no se pudo leer .dockerignore

Sin dependencias: sólo la biblioteca estándar, para que corra en el job de
lint más barato sin instalar nada.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path

# ── Las semillas que un comando de publicación lee por omisión ───────────
#
# (ruta relativa a la raíz del repo, quién la lee)
SEMILLAS_REQUERIDAS: list[tuple[str, str]] = [
    (
        "data/labor/articulos_vigentes.json",
        "manage.py publish_law_articles (textos de artículos con vigencia, T-1a)",
    ),
    (
        "data/labor/sat_catalogos.json",
        "manage.py publish_labor_rules (catálogos del SAT, T-1b)",
    ),
    # Los registros: ya estaban re-incluidos y el Dockerfile los COPYa
    # explícitamente, pero vigilarlos aquí cierra el hueco por el que se
    # colaron las semillas laborales. El incidente del 2026-08-27 (ingest del
    # Reglamento de la LFPDPPP muerto con FileNotFoundError, resuelto
    # copiando el archivo al pod a mano) es exactamente este bug.
    (
        "data/law_registry.json",
        "LawRegistry (apps/scraper/utils/law_registry.py) y dataops.ingest_law",
    ),
    (
        "data/universe_registry.json",
        "coverage_dashboard y /api/v1/coverage/ — sin él, literales hardcodeados",
    ),
    (
        "data/discovered_reglamentos.json",
        "apps/scraper/dataops/coverage_dashboard.py",
    ),
]


@dataclass
class Regla:
    """Un patrón de .dockerignore, con su número de línea para el reporte."""

    lineno: int
    patron: str
    negado: bool  # empieza con '!' → re-inclusión


def parse_dockerignore(texto: str) -> list[Regla]:
    """Lee .dockerignore respetando comentarios, blancos y '!'."""
    reglas: list[Regla] = []
    for lineno, raw in enumerate(texto.splitlines(), start=1):
        linea = raw.strip()
        if not linea or linea.startswith("#"):
            continue
        negado = linea.startswith("!")
        patron = linea[1:].strip() if negado else linea
        # Docker normaliza separadores y quita el './' inicial.
        patron = patron.lstrip("./") if patron.startswith("./") else patron
        patron = patron.rstrip("/")
        if not patron:
            continue
        reglas.append(Regla(lineno=lineno, patron=patron, negado=negado))
    return reglas


def patron_casa(patron: str, ruta: str) -> bool:
    """¿Este patrón de .dockerignore casa con esta ruta?

    Docker casa el patrón contra la ruta COMPLETA relativa al contexto, y un
    patrón que casa un directorio arrastra todo lo que cuelga de él (`docs/`
    excluye `docs/labor/README.md`). fnmatch por sí solo no modela esa
    segunda parte, así que se comprueba también contra cada prefijo de
    directorio de la ruta.
    """
    if fnmatch(ruta, patron):
        return True
    # ¿Casa algún directorio ancestro? (`data` o `data/*` vs `data/labor/x.json`)
    partes = ruta.split("/")
    for i in range(1, len(partes)):
        prefijo = "/".join(partes[:i])
        if fnmatch(prefijo, patron):
            return True
    return False


def esta_excluida(ruta: str, reglas: list[Regla]) -> Regla | None:
    """Aplica las reglas en orden; gana la ÚLTIMA que casa (regla de Docker).

    Devuelve la regla de exclusión que gana, o None si la ruta viaja en la
    imagen.
    """
    ganadora: Regla | None = None
    for regla in reglas:
        if patron_casa(regla.patron, ruta):
            ganadora = regla
    if ganadora is None:
        return None  # ningún patrón la toca → se incluye
    return None if ganadora.negado else ganadora


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Falla si una semilla que un comando de publicación necesita "
            "queda fuera de la imagen por .dockerignore."
        )
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Raíz del repo (por omisión, el directorio actual)",
    )
    args = parser.parse_args(argv[1:])

    root = Path(args.repo_root).resolve()
    dockerignore = root / ".dockerignore"
    if not dockerignore.is_file():
        print(f"error: no existe {dockerignore}", file=sys.stderr)
        return 2

    try:
        reglas = parse_dockerignore(dockerignore.read_text(encoding="utf-8"))
    except OSError as exc:
        print(f"error: no se pudo leer {dockerignore}: {exc}", file=sys.stderr)
        return 2

    fallos: list[str] = []

    for ruta, lector in SEMILLAS_REQUERIDAS:
        # 1. ¿Existe en el árbol? Un .dockerignore correcto sobre un archivo
        #    que ya no está produce el MISMO síntoma en el pod.
        if not (root / ruta).is_file():
            fallos.append(
                f"{ruta}: NO EXISTE en el árbol, y {lector} la lee por "
                "omisión. Si se renombró, actualiza SEMILLAS_REQUERIDAS y el "
                "comando; si se borró, el comando queda roto en el pod."
            )
            continue

        # 2. ¿Viaja en la imagen?
        excluyente = esta_excluida(ruta, reglas)
        if excluyente is not None:
            fallos.append(
                f"{ruta}: EXCLUIDA de la imagen por el patrón "
                f"`{excluyente.patron}` (.dockerignore:{excluyente.lineno}). "
                f"La lee {lector}. Dentro del pod ese comando aborta sin "
                "escribir, y el feed se queda vacío. Re-inclúyela con una "
                f"línea `!{ruta}` (o `!data/<dir>/`) DESPUÉS de ese patrón."
            )

    for f in fallos:
        print(f"[FAIL] {f}")

    print()
    print(
        f"revisadas {len(SEMILLAS_REQUERIDAS)} semilla(s) contra "
        f"{len(reglas)} regla(s) de .dockerignore; {len(fallos)} fallo(s)."
    )

    if fallos:
        print(
            "FAIL: al menos una semilla no viajaría en la imagen. "
            "Ver los mensajes de arriba.",
            file=sys.stderr,
        )
        return 1

    print("OK: todas las semillas de publicación viajan en la imagen.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
