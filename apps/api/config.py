"""Centralized configuration for the API app."""

import logging
import os

from elasticsearch import Elasticsearch

logger = logging.getLogger(__name__)

ES_HOST = os.getenv("ES_HOST", "http://elasticsearch:9200")
INDEX_NAME = "articles"

# Alias-based index versioning (INDEX_NAME still works — ES resolves aliases on reads)
INDEX_ALIAS = "articles"
INDEX_PREFIX = "articles_v"

# ES client configuration for production resilience
ES_TIMEOUT = int(os.getenv("ES_TIMEOUT", "30"))
ES_MAX_RETRIES = int(os.getenv("ES_MAX_RETRIES", "3"))
ES_RETRY_ON_TIMEOUT = os.getenv("ES_RETRY_ON_TIMEOUT", "true").lower() == "true"

# Optional basic-auth credentials. When unset the client connects without auth,
# preserving the legacy compose-stack behaviour. When set (recommended in any
# environment with xpack.security.enabled), the client authenticates as that
# user.
ES_USERNAME = os.getenv("ES_USERNAME") or None
ES_PASSWORD = os.getenv("ES_PASSWORD") or None

_es_kwargs = {
    "request_timeout": ES_TIMEOUT,
    "max_retries": ES_MAX_RETRIES,
    "retry_on_timeout": ES_RETRY_ON_TIMEOUT,
    "sniff_on_start": False,
}
if ES_USERNAME and ES_PASSWORD:
    _es_kwargs["basic_auth"] = (ES_USERNAME, ES_PASSWORD)

# Singleton ES client with retry and timeout (ES 8.x)
es_client = Elasticsearch([ES_HOST], **_es_kwargs)
