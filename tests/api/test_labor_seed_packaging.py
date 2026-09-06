"""Las semillas laborales tienen que estar donde los comandos las buscan (T-1d).

La compuerta falsable de este carril. Sobre ``main`` estas pruebas están en
**rojo**, y por dos razones distintas que conviene no confundir:

1. ``TestRutasPorOmision`` corre desde un cwd que **no** es la raíz del repo.
   Sobre ``main`` los valores por omisión son ``Path("data")/...``, relativos
   al directorio de trabajo, así que ahí no resuelven a nada y el comando
   aborta con «No existe el seed» — que es exactamente lo que se vio en el pod
   el 2026-09-06, indistinguible de un seed genuinamente ausente.

2. ``TestSemillasViajanEnLaImagen`` simula ``.dockerignore``. Sobre ``main``,
   ``data/*`` excluye ``data/labor/*.json`` y la prueba nombra el patrón
   culpable.

El bug que las motiva no fue un error de los comandos: los dos fallaron
**limpiamente y sin escribir** (fail-closed correcto). Lo que faltaba era el
archivo, y el costo aguas abajo es un feed laboral vacío y un symbiosis-hcm
—fail-closed contra Tezca— incapaz de publicar una sola obligación.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

# Las mismas rutas que vigila scripts/check-dockerignore-seeds.py, declaradas
# aquí con el comando que las lee para que el fallo diga qué se rompe.
SEMILLAS = [
    ("data/labor/articulos_vigentes.json", "publish_law_articles"),
    ("data/labor/sat_catalogos.json", "publish_labor_rules"),
]


def _cargar_checker():
    """Importa scripts/check-dockerignore-seeds.py por ruta.

    Lleva guiones en el nombre —es un ejecutable de CI, no un módulo— así que
    no se puede `import` por nombre. Se reutiliza aquí a propósito: la prueba y
    el chequeo de CI comparten la misma simulación de `.dockerignore`, y no dos
    implementaciones que puedan discrepar.
    """
    import importlib.util

    nombre = "check_dockerignore_seeds"
    if nombre in sys.modules:
        return sys.modules[nombre]

    ruta = REPO_ROOT / "scripts" / "check-dockerignore-seeds.py"
    spec = importlib.util.spec_from_file_location(nombre, ruta)
    assert spec is not None and spec.loader is not None, f"no se pudo cargar {ruta}"
    modulo = importlib.util.module_from_spec(spec)
    # Registrar ANTES de ejecutar: el script define dataclasses, y
    # `@dataclass` resuelve las anotaciones mirando `sys.modules[__module__]`.
    # Sin este registro previo revienta con AttributeError sobre None.
    sys.modules[nombre] = modulo
    try:
        spec.loader.exec_module(modulo)
    except Exception:
        del sys.modules[nombre]
        raise
    return modulo


class TestRutasPorOmision:
    """El valor por omisión resuelve —y existe— desde cualquier cwd."""

    @pytest.mark.parametrize("ruta,comando", SEMILLAS)
    def test_la_semilla_existe_en_el_arbol(self, ruta, comando):
        """Sin el archivo, `manage.py <comando>` aborta dentro del pod."""
        assert (
            REPO_ROOT / ruta
        ).is_file(), f"falta {ruta}, que {comando} lee por omisión"

    def test_default_seed_es_absoluto_y_existe(self):
        from apps.api.management.commands.publish_law_articles import DEFAULT_SEED

        assert Path(DEFAULT_SEED).is_absolute(), (
            "DEFAULT_SEED es relativo: el comando sólo funcionaría parado en la "
            "raíz del repo, y desde cualquier otro cwd abortaría con «No existe "
            "el seed» — el síntoma observado en producción el 2026-09-06."
        )
        assert Path(DEFAULT_SEED).is_file(), f"DEFAULT_SEED no existe: {DEFAULT_SEED}"

    def test_default_catalogos_es_absoluto_y_existe(self):
        from apps.api.management.commands.publish_labor_rules import DEFAULT_CATALOGOS

        assert Path(DEFAULT_CATALOGOS).is_absolute(), (
            "DEFAULT_CATALOGOS es relativo: el fail-closed de la lectura del "
            "catálogo se dispararía por estar parado en el directorio "
            "equivocado, no sólo por un catálogo ausente."
        )
        assert Path(
            DEFAULT_CATALOGOS
        ).is_file(), f"DEFAULT_CATALOGOS no existe: {DEFAULT_CATALOGOS}"

    def test_las_rutas_resuelven_desde_otro_cwd(self, tmp_path):
        """El corazón de la compuerta: rojo sobre `main`.

        Se resuelven los valores por omisión en un subproceso cuyo cwd es un
        directorio temporal, no la raíz del repo. Con rutas relativas los dos
        `is_file()` dan False; ancladas a `BASE_DIR` dan True.
        """
        codigo = (
            "import django, os; "
            "os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'apps.indigo.settings'); "
            "django.setup(); "
            "from pathlib import Path; "
            "from apps.api.management.commands.publish_law_articles "
            "import DEFAULT_SEED; "
            "from apps.api.management.commands.publish_labor_rules "
            "import DEFAULT_CATALOGOS; "
            "print(Path(DEFAULT_SEED).is_file(), Path(DEFAULT_CATALOGOS).is_file())"
        )
        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join([str(REPO_ROOT / "apps"), str(REPO_ROOT)])
        env["DJANGO_SETTINGS_MODULE"] = "apps.indigo.settings"

        proc = subprocess.run(
            [sys.executable, "-c", codigo],
            cwd=tmp_path,  # ← deliberadamente NO la raíz del repo
            env=env,
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, f"el subproceso falló:\n{proc.stderr}"
        assert proc.stdout.strip() == "True True", (
            "desde un cwd que no es la raíz del repo, los valores por omisión "
            f"no resuelven a un archivo existente (salida: {proc.stdout.strip()!r}). "
            "Ánclalos a settings.BASE_DIR en vez de a Path('data')."
        )


class TestSemillasViajanEnLaImagen:
    """`.dockerignore` no puede volver a dejar las semillas fuera."""

    @pytest.mark.parametrize("ruta,comando", SEMILLAS)
    def test_la_semilla_no_esta_excluida(self, ruta, comando):
        modulo = _cargar_checker()
        reglas = modulo.parse_dockerignore(
            (REPO_ROOT / ".dockerignore").read_text(encoding="utf-8")
        )
        excluyente = modulo.esta_excluida(ruta, reglas)
        assert excluyente is None, (
            f"{ruta} queda fuera de la imagen por `{excluyente.patron}` "
            f"(.dockerignore:{excluyente.lineno}); dentro del pod "
            f"`manage.py {comando}` aborta sin escribir y el feed laboral "
            "se queda vacío."
        )

    def test_el_dockerfile_copia_las_semillas(self):
        """La aserción ruidosa del Dockerfile sigue en su sitio.

        Si un builder pierde la re-inclusión de `.dockerignore`, este COPY
        hace fallar el build en vez de producir una imagen que sólo se
        descubre rota cuando un operador entra al pod a publicar.
        """
        dockerfile = (REPO_ROOT / "apps" / "indigo" / "Dockerfile").read_text(
            encoding="utf-8"
        )
        for ruta, _ in SEMILLAS:
            assert ruta in dockerfile, (
                f"{ruta} ya no se COPYa explícitamente en apps/indigo/Dockerfile: "
                "se pierde la aserción que convierte una re-inclusión rota en un "
                "build fallido en vez de una imagen silenciosamente incompleta."
            )
