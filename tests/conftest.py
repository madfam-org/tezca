"""
Shared pytest fixtures for testing.
"""

import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

# Add apps to path for all tests
sys.path.insert(0, str(Path(__file__).parent.parent / "apps"))
sys.path.insert(0, str(Path(__file__).parent.parent))

# ── El broker de la suite vive en memoria ───────────────────────────────
#
# `apps/indigo/settings.py` fija `CELERY_TASK_ALWAYS_EAGER` y el broker en
# memoria cuando detecta que corre bajo pruebas; ahí está el porqué completo.
# Esto cierra los dos huecos que el módulo de settings no alcanza, y se hace en
# el import de conftest — antes de que Django o Celery lean nada.
#
# 1. Celery lee `CELERY_BROKER_URL` del ENTORNO y el entorno gana sobre el
#    objeto de settings de Django. Verificado: con `CELERY_BROKER_URL` exportado,
#    `celery_app.conf.broker_url` seguía siendo esa URL aunque
#    `settings.CELERY_BROKER_URL` dijera `memory://`. Con eager encendido nada
#    marcaba a la red, pero dejar el broker apuntando a un Redis es apoyarse en
#    una sola línea de defensa.
# 2. `apps/api/billing_stream_consumer._get_redis_client()` no lee settings sino
#    `os.environ`, cayendo a `CELERY_BROKER_URL` y de ahí a
#    `redis://localhost:6379/0`.
#
# Se SOBREESCRIBE (no `setdefault`): un `CELERY_BROKER_URL` heredado del shell
# del desarrollador o de un job de CI es justamente lo que vuelve ambiental el
# resultado de la suite. Quien de verdad necesite un broker real en una prueba
# debe pedirlo explícitamente en esa prueba, no por variable de entorno.
os.environ["CELERY_BROKER_URL"] = "memory://"
os.environ["CELERY_RESULT_BACKEND"] = "cache+memory://"


@pytest.fixture
def celery_eager_off(settings):
    """Apaga `task_always_eager` SÓLO dentro de la prueba que lo pida.

    Para pruebas de *wiring* que necesitan comprobar que algo se ENCOLA (que
    `apply_async` fue llamado) en vez de que se ejecute. El broker sigue siendo
    `memory://`, así que ni siquiera con eager apagado se toca la red; aun así,
    mockea el `.delay()`/`apply_async` de la tarea concreta en la prueba en vez
    de dejar que kombu haga el viaje.
    """
    settings.CELERY_TASK_ALWAYS_EAGER = False
    settings.CELERY_TASK_EAGER_PROPAGATES = False

    from apps.indigo.celery import app as celery_app

    previous = (
        celery_app.conf.task_always_eager,
        celery_app.conf.task_eager_propagates,
    )
    celery_app.conf.task_always_eager = False
    celery_app.conf.task_eager_propagates = False
    try:
        yield celery_app
    finally:
        (
            celery_app.conf.task_always_eager,
            celery_app.conf.task_eager_propagates,
        ) = previous


@pytest.fixture(autouse=True)
def _use_dummy_cache(request):
    """Override Redis cache with in-memory dummy cache for Django tests."""
    try:
        from django.conf import settings as django_settings
        from django.test.utils import override_settings

        with override_settings(
            CACHES={
                "default": {
                    "BACKEND": "django.core.cache.backends.dummy.DummyCache",
                }
            }
        ):
            yield
    except Exception:
        yield


@pytest.fixture
def sample_law_text():
    """Sample law text with basic structure."""
    return """
TÍTULO PRIMERO
De las Disposiciones Generales

CAPÍTULO I
Disposiciones Generales

Artículo 1.- Esta es una ley de prueba.

Artículo 2.- Las disposiciones de esta ley son de orden público.

I. Primera fracción.
II. Segunda fracción.

Artículo 3.- Se deroga.

TRANSITORIOS

PRIMERO.- Esta ley entrará en vigor el día siguiente al de su publicación.

SEGUNDO.- Se derogan todas las disposiciones que se opongan al presente decreto.
""".strip()


@pytest.fixture
def temp_data_dir(tmp_path):
    """Create temporary data directory structure."""
    data_dir = tmp_path / "data"
    (data_dir / "raw" / "pdfs").mkdir(parents=True)
    (data_dir / "federal").mkdir(parents=True)
    (data_dir / "logs").mkdir(parents=True)
    return data_dir


@pytest.fixture
def sample_law_metadata():
    """Sample law metadata."""
    return {
        "id": "test-law",
        "name": "Ley de Prueba",
        "short_name": "Ley de Prueba",
        "type": "ley",
        "slug": "test",
        "expected_articles": 3,
        "publication_date": "2020-01-01",
        "source": "chamber",
        "url": "https://example.com/test.pdf",
        "priority": 1,
        "tier": "test",
        "status": "active",
    }


@pytest.fixture
def basic_akn_xml():
    """Minimal valid Akoma Ntoso XML."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<akomaNtoso xmlns="http://docs.oasis-open.org/legaldocml/ns/akn/3.0">
  <act name="test">
    <meta>
      <identification source="#source">
        <FRBRWork>
          <FRBRthis value="/mx/act/2020/test"/>
          <FRBRuri value="/mx/act/2020/test"/>
          <FRBRdate date="2020-01-01" name="Generation"/>
        </FRBRWork>
      </identification>
    </meta>
    <body>
      <article id="art-1">
        <num>Artículo 1</num>
        <content>
          <p>Test content.</p>
        </content>
      </article>
    </body>
  </act>
</akomaNtoso>"""
