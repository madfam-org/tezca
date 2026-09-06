"""La suite no depende de que haya un broker en la máquina.

El 2026-09-06, ``test_corpus_watch.py::test_watch_hits_are_recorded_and_returned``
fallaba en local y pasaba en CI. La causa no estaba en la prueba: **en CI no hay
Redis**. ``deliver_operator_alert.delay()`` lanzaba
``kombu.exceptions.OperationalError``, un ``except Exception`` amplio se lo
tragaba, y la ruta ejecutada cambiaba según si el desarrollador tenía un
``redis-server`` escuchando. Exactamente 1 de ~2900 pruebas era sensible, pero
la clase entera seguía abierta: la configuración de pruebas no fijaba nada de
Celery, así que cualquier ``.delay()`` nuevo heredaba la misma dependencia del
entorno.

Estas pruebas son la compuerta falsable de la corrección. Fallan si alguien
quita el bloque ``if RUNNING_TESTS`` de ``apps/indigo/settings.py``, si el
detector de modo prueba deja de disparar, o si el broker de la suite vuelve a
apuntar a un Redis local.
"""

from __future__ import annotations

import os
from urllib.parse import urlparse

import pytest
from celery import shared_task
from django.conf import settings

from apps.indigo.celery import app as celery_app

# ---------------------------------------------------------------------------
# La configuración
# ---------------------------------------------------------------------------


def test_eager_esta_encendido_bajo_pytest():
    """Sin eager, un ``.delay()`` sale a la red y la suite se vuelve ambiental."""
    assert settings.RUNNING_TESTS is True, (
        "settings.RUNNING_TESTS debe detectar que corremos bajo pytest; si no, "
        "todo el bloque de Celery para pruebas queda inerte"
    )
    assert settings.CELERY_TASK_ALWAYS_EAGER is True


def test_el_detector_no_se_dispara_por_tener_pytest_importado():
    """La producción NO debe caer en modo pruebas por importar pytest.

    La imagen de producción corre ``poetry install`` sin ``--only main``, así
    que pytest viaja en ella. Si ``RUNNING_TESTS`` mirara ``sys.modules``, un
    solo ``import pytest`` en código de prod pondría la producción en eager con
    un broker en memoria: las tareas se ejecutarían dentro del request y nada
    volvería a encolarse. El detector debe depender de señales de *invocación*
    (variables que exporta el runner, ``sys.argv``), no de qué está importado.
    """
    import ast
    import inspect

    from apps.indigo import settings as settings_module

    arbol = ast.parse(inspect.getsource(settings_module))
    asignaciones = [
        nodo
        for nodo in arbol.body
        if isinstance(nodo, ast.Assign)
        and any(
            isinstance(t, ast.Name) and t.id == "RUNNING_TESTS" for t in nodo.targets
        )
    ]
    assert (
        len(asignaciones) == 1
    ), "se esperaba exactamente una asignación de RUNNING_TESTS"

    expresion = ast.unparse(asignaciones[0].value)
    assert "sys.modules" not in expresion, (
        "RUNNING_TESTS no debe consultar sys.modules: pytest está instalado en "
        "la imagen de producción y cualquier import lo activaría"
    )


def test_eager_propaga_los_errores_de_la_tarea():
    """Eager sin propagación convierte una tarea rota en una prueba verde.

    Con ``task_eager_propagates`` apagado, una excepción dentro de la tarea se
    guarda en el ``EagerResult`` y nadie la mira: la prueba pasa igual. Con él
    encendido, la excepción sale por donde se llamó ``.delay()``.
    """
    assert settings.CELERY_TASK_EAGER_PROPAGATES is True


def test_la_app_de_celery_hereda_la_config_de_pruebas():
    """El seam real es la app, no sólo el módulo de settings.

    ``apps/indigo/celery.py`` hace ``config_from_object("django.conf:settings",
    namespace="CELERY")``. Si esa cadena se rompiera, ``settings`` diría eager y
    la app seguiría marcando al broker. Esto lo comprueba en la app misma.
    """
    assert celery_app.conf.task_always_eager is True
    assert celery_app.conf.task_eager_propagates is True


# ---------------------------------------------------------------------------
# El broker
# ---------------------------------------------------------------------------


def test_el_broker_de_pruebas_no_apunta_a_un_redis_local():
    """Ni `localhost:6379` ni ningún otro Redis: el transporte vive en memoria."""
    for nombre, url in (
        ("CELERY_BROKER_URL", settings.CELERY_BROKER_URL),
        ("CELERY_RESULT_BACKEND", settings.CELERY_RESULT_BACKEND),
    ):
        parsed = urlparse(url)
        assert parsed.scheme.startswith(("memory", "cache+memory")), (
            f"{nombre} = {url!r} — bajo pruebas debe ser un transporte en "
            "memoria, no una URL de red"
        )
        assert "6379" not in url, f"{nombre} = {url!r} apunta al puerto de Redis"
        assert (
            "localhost" not in url and "127.0.0.1" not in url
        ), f"{nombre} = {url!r} apunta a un servicio local"


def test_el_broker_de_la_app_tampoco_apunta_a_redis():
    assert "6379" not in celery_app.conf.broker_url
    assert celery_app.conf.broker_url.startswith("memory")


def test_el_entorno_de_pruebas_tambien_lleva_el_broker_en_memoria():
    """Para el código que lee ``os.environ`` en vez de ``django.conf.settings``.

    ``apps/api/billing_stream_consumer._get_redis_client()`` cae a
    ``CELERY_BROKER_URL`` del entorno. ``tests/conftest.py`` lo fija en el
    import; sin eso, ese camino marcaría a ``redis://localhost:6379/0`` aunque
    los settings de Django estuvieran bien.
    """
    url = os.environ.get("CELERY_BROKER_URL", "")
    assert url, "tests/conftest.py debe fijar CELERY_BROKER_URL en el entorno"
    assert "6379" not in url, f"CELERY_BROKER_URL={url!r} apunta a Redis"


# ---------------------------------------------------------------------------
# El comportamiento observable: `.delay()` corre aquí mismo, sin broker
# ---------------------------------------------------------------------------


_ejecuciones: list[tuple[int, int]] = []


@shared_task(name="tests.suma_trivial")
def suma_trivial(a: int, b: int) -> int:
    """Tarea trivial, sólo para observar dónde se ejecuta."""
    _ejecuciones.append((a, b))
    return a + b


@shared_task(name="tests.explota")
def explota() -> None:
    raise ValueError("la tarea falló")


def test_delay_corre_en_el_mismo_proceso_sin_broker():
    """Esta es la aserción que importa: no hay red de por medio.

    Si eager estuviera apagado y no hubiera Redis, ``.delay()`` levantaría
    ``kombu.exceptions.OperationalError`` en vez de devolver un resultado. Si
    hubiera Redis, la tarea se encolaría y ``_ejecuciones`` quedaría vacío: la
    prueba distingue los tres casos.
    """
    _ejecuciones.clear()

    resultado = suma_trivial.delay(2, 3)

    assert resultado.get(timeout=1) == 5
    assert _ejecuciones == [
        (2, 3)
    ], "la tarea no corrió en este proceso — se encoló en un broker de verdad"


def test_apply_async_tambien_corre_aqui():
    """La otra puerta al broker, no sólo el azúcar ``.delay()``."""
    _ejecuciones.clear()

    resultado = suma_trivial.apply_async(args=(7, 5))

    assert resultado.get(timeout=1) == 12
    assert _ejecuciones == [(7, 5)]


def test_un_fallo_dentro_de_la_tarea_sale_a_la_prueba():
    """La contraparte observable de ``task_eager_propagates``."""
    with pytest.raises(ValueError, match="la tarea falló"):
        explota.delay()


# ---------------------------------------------------------------------------
# La válvula de escape
# ---------------------------------------------------------------------------


def test_el_fixture_celery_eager_off_apaga_eager_solo_en_su_ambito(celery_eager_off):
    """Para pruebas de wiring que comprueban el ENCOLADO, no la ejecución."""
    assert celery_eager_off.conf.task_always_eager is False


def test_eager_vuelve_a_estar_encendido_despues_del_fixture():
    """El fixture no debe filtrar su estado a la prueba siguiente."""
    assert celery_app.conf.task_always_eager is True
