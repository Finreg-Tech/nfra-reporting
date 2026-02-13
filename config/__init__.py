"""
Configuration package for Fin-LLM-NFRA.

This package contains:
- settings.py: Application configuration (API keys, database URLs, etc.)
- logging.py: Centralized logging configuration
"""

from config.logging import get_logger, configure_logging
from config.settings import (
    BASE_DIR,
    ML_MODELS_DIR,
    RESULTS_DIR,
    PROMPTS_DIR,
    KNOWLEDGE_GRAPH_PATH,
    LOG_LEVEL,
    LOG_FORMAT,
    MAX_FILE_SIZE_BYTES,
    MAX_LLAMAPARSE_WORKERS,
    LLM_RETRY_COUNT,
    OPENAI_API_KEY,
    OPENAI_MODEL,
    OPENAI_TEMPERATURE,
    LLAMA_CLOUD_API_KEY,
    API_HOST,
    API_PORT,
    PROMPT_FILES,
    ALLOWED_CATEGORIES,
    HEADER_KEYWORDS,
    LIGATURES,
    ML_VECTORIZER_PATH,
    ML_CLASSIFIER_PATH,
)

__all__ = [
    "get_logger",
    "configure_logging",
    "BASE_DIR",
    "ML_MODELS_DIR",
    "RESULTS_DIR",
    "PROMPTS_DIR",
    "KNOWLEDGE_GRAPH_PATH",
    "LOG_LEVEL",
    "LOG_FORMAT",
    "MAX_FILE_SIZE_BYTES",
    "MAX_LLAMAPARSE_WORKERS",
    "LLM_RETRY_COUNT",
    "OPENAI_API_KEY",
    "OPENAI_MODEL",
    "OPENAI_TEMPERATURE",
    "LLAMA_CLOUD_API_KEY",
    "API_HOST",
    "API_PORT",
    "PROMPT_FILES",
    "ALLOWED_CATEGORIES",
    "HEADER_KEYWORDS",
    "LIGATURES",
    "ML_VECTORIZER_PATH",
    "ML_CLASSIFIER_PATH",
]
