import os
from pathlib import Path
from typing import Final
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# Directory Paths
# =============================================================================

BASE_DIR: Final[Path] = Path(__file__).resolve().parent.parent
ML_MODELS_DIR: Final[Path] = BASE_DIR / "resources" / "models"
RESULTS_DIR: Final[Path] = BASE_DIR / "results"
PROMPTS_DIR: Final[Path] = BASE_DIR / "resources" / "prompts"
KNOWLEDGE_GRAPH_PATH: Final[Path] = PROMPTS_DIR / "knowledge_graph.json"

# =============================================================================
# Logging Configuration
# =============================================================================

LOG_LEVEL: Final[str] = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT: Final[str] = os.getenv(
    "LOG_FORMAT", 
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# =============================================================================
# API & Processing Configuration
# =============================================================================

MAX_FILE_SIZE_BYTES: Final[int] = int(os.getenv("MAX_FILE_SIZE_BYTES", 50 * 1024 * 1024))
MAX_LLAMAPARSE_WORKERS: Final[int] = int(os.getenv("MAX_LLAMAPARSE_WORKERS", 3))
LLM_RETRY_COUNT: Final[int] = int(os.getenv("LLM_RETRY_COUNT", 2))

OPENAI_API_KEY: Final[str] = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL: Final[str] = os.getenv("OPENAI_MODEL", "gpt-4o")
OPENAI_TEMPERATURE: Final[float] = float(os.getenv("OPENAI_TEMPERATURE", 0))

LLAMA_CLOUD_API_KEY: Final[str] = os.getenv("LLAMA_CLOUD_API_KEY")

API_HOST: Final[str] = os.getenv("API_HOST", "0.0.0.0")
API_PORT: Final[int] = int(os.getenv("API_PORT", "8000"))

PROMPT_FILES: Final[dict[str, Path]] = {
    "balance_sheet": PROMPTS_DIR / "BS.j2",
    "profit_loss": PROMPTS_DIR / "PL.j2",
    "cash_flow": PROMPTS_DIR / "CF.j2"
}

ALLOWED_CATEGORIES: Final[frozenset[str]] = frozenset({"BS", "PL", "Cash Flow"})

HEADER_KEYWORDS: Final[dict[str, list[str]]] = {
    "BS": ["balance sheet", "statement of assets and liabilities"],
    "PL": ["income statement", "profit and loss", "profit & loss", "statement of profit and loss"],
    "Cash Flow": ["cash flow", "statement of cash flow"]
}

LIGATURES: Final[dict[str, str]] = {
    "ﬁ": "fi",
    "ﬂ": "fl",
    "ﬀ": "ff",
    "ﬃ": "ffi",
    "ﬄ": "ffl"
}

ML_VECTORIZER_PATH: Final[Path] = ML_MODELS_DIR / "LR_NFRA_vectorizer.pkl"
ML_CLASSIFIER_PATH: Final[Path] = ML_MODELS_DIR / "LR_NFRA_CLASSIFIER.pkl"
