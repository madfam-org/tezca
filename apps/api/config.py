"""Centralized configuration for the API app."""

import logging
import os

from elasticsearch import Elasticsearch

logger = logging.getLogger(__name__)

ES_HOST = os.getenv("ES_HOST", "http://elasticsearch:9200")
INDEX_NAME = "articles"

# ES client configuration for production resilience
ES_TIMEOUT = int(os.getenv("ES_TIMEOUT", "30"))
ES_MAX_RETRIES = int(os.getenv("ES_MAX_RETRIES", "3"))
ES_RETRY_ON_TIMEOUT = os.getenv("ES_RETRY_ON_TIMEOUT", "true").lower() == "true"

# Singleton ES client with retry and timeout (ES 8.x)
es_client = Elasticsearch(
    [ES_HOST],
    request_timeout=ES_TIMEOUT,
    max_retries=ES_MAX_RETRIES,
    retry_on_timeout=ES_RETRY_ON_TIMEOUT,
    sniff_on_start=False,
)
