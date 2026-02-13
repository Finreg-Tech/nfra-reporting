"""
Centralized logging configuration for Fin-LLM-NFRA.

Usage:
    from config.logging import get_logger
    logger = get_logger(__name__)
"""

import logging
import sys
from pathlib import Path
from typing import Optional

# Try to import settings, but provide defaults if not available
try:
    from config.settings import LOG_LEVEL, LOG_FORMAT
except ImportError:
    LOG_LEVEL = "INFO"
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


# =============================================================================
# Logging Configuration
# =============================================================================

_CONFIGURED = False


def configure_logging(
    level: str = LOG_LEVEL,
    format_string: str = LOG_FORMAT,
    log_file: Optional[Path] = None,
) -> None:
    """
    Configure the root logger for the application.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_string: Log message format
        log_file: Optional file path to write logs
    """
    global _CONFIGURED
    
    if _CONFIGURED:
        return
    
    # Create formatter
    formatter = logging.Formatter(format_string)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    
    # File handler (optional)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        root_logger.addHandler(file_handler)
    
    # Suppress noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.
    
    This ensures logging is configured before returning the logger.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured logger instance
    """
    configure_logging()
    return logging.getLogger(name)


# =============================================================================
# Module-Level Configuration
# =============================================================================

# Auto-configure on import
configure_logging()
