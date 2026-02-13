import logging
import os
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import fitz
import joblib
from llama_parse import LlamaParse

from config import (
    ALLOWED_CATEGORIES,
    HEADER_KEYWORDS,
    LLAMA_CLOUD_API_KEY,
    MAX_LLAMAPARSE_WORKERS,
    ML_CLASSIFIER_PATH,
    ML_VECTORIZER_PATH,
)
from src.services.extraction.llm.normalizer import normalize_category, normalize_text

logger = logging.getLogger(__name__)

_vectorizer = None
_model = None


def _load_ml_models():
    global _vectorizer, _model
    if _vectorizer is None or _model is None:
        logger.info("Loading ML models")
        _vectorizer = joblib.load(ML_VECTORIZER_PATH)
        _model = joblib.load(ML_CLASSIFIER_PATH)
        logger.info("ML models loaded")
    return _vectorizer, _model


def _extract_header_text(page, header_ratio: float = 0.15) -> str:
    rect = page.rect
    header_rect = fitz.Rect(rect.x0, rect.y0, rect.x1, rect.y0 + rect.height * header_ratio)
    return normalize_text(page.get_text(clip=header_rect))


def _is_notes_page(header_text: str) -> bool:
    return header_text.startswith("notes")


def _classify_pages(pdf_path: str) -> dict[str, list[int]]:
    vectorizer, model = _load_ml_models()

    logger.info("Opening PDF: %s", Path(pdf_path).name)
    doc = fitz.open(pdf_path)
    logger.info("PDF has %d pages", len(doc))

    category_pages: dict[str, list[int]] = {}
    for page_num in range(len(doc)):
        text = doc[page_num].get_text()
        if not text.strip():
            continue

        cleaned = normalize_text(text)
        pred = normalize_category(model.predict(vectorizer.transform([cleaned]))[0])

        if pred != "Others":
            category_pages.setdefault(pred, []).append(page_num)

    doc.close()
    logger.info("Categories found: %s", list(category_pages.keys()))
    return category_pages


def _key_matching(pdf_path: str, category_pages: dict[str, list[int]]) -> dict[str, list[int]]:
    doc = fitz.open(pdf_path)
    filtered: dict[str, list[int]] = {}

    for category, pages in category_pages.items():
        if category not in ("BS", "PL", "Cash Flow"):
            filtered[category] = pages
            continue

        keywords = HEADER_KEYWORDS.get(category, [])
        matched = []

        for page_num in pages:
            header = _extract_header_text(doc[page_num])
            if _is_notes_page(header):
                continue
            if any(kw in header for kw in keywords):
                matched.append(page_num)

        filtered[category] = matched

    doc.close()
    return filtered


def _create_category_pdf(pdf_path: str, page_indices: list[int]) -> bytes:
    doc = fitz.open(pdf_path)
    new_doc = fitz.open()
    for p in page_indices:
        new_doc.insert_pdf(doc, from_page=p, to_page=p)
    pdf_bytes = new_doc.tobytes()
    new_doc.close()
    doc.close()
    return pdf_bytes


def _parse_category_worker(
    api_key: str,
    pdf_path: str,
    category: str,
    pages: list[int]
) -> dict[str, Any]:
    start_time = time.time()
    logger.info("Processing %s (%d pages)", category, len(pages))

    temp_path: str | None = None
    try:
        parser = LlamaParse(
            api_key=api_key,
            result_type="markdown",
            verbose=False,
            language="en"
        )

        pdf_bytes = _create_category_pdf(pdf_path, pages)

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(pdf_bytes)
            temp_path = f.name

        docs = parser.load_data(temp_path)
        markdown = "\n\n".join([d.text for d in docs])

        elapsed = time.time() - start_time
        logger.info("%s completed in %.2fs", category, elapsed)

        return {
            "category": category,
            "status": "success",
            "markdown": markdown,
            "time": elapsed
        }

    except Exception as e:
        logger.error("Error processing %s: %s", category, e)
        return {
            "category": category,
            "status": "error",
            "error": str(e),
            "markdown": None
        }
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except OSError:
                pass


def extract_financial_markdown(
    pdf_path: str,
    company_name: str | None = None,
    max_workers: int = MAX_LLAMAPARSE_WORKERS
) -> dict[str, str | None]:
    pdf_name = company_name if company_name else Path(pdf_path).stem

    category_pages = _classify_pages(pdf_path)
    filtered = {k: v for k, v in category_pages.items() if k in ALLOWED_CATEGORIES}
    filtered = _key_matching(pdf_path, filtered)

    llamaparse_categories = {k: v for k, v in filtered.items() if v}

    if not llamaparse_categories:
        logger.warning("No valid financial statement pages found")
        return {
            "company_name": pdf_name,
            "balance_sheet_md": None,
            "profit_loss_md": None,
            "cash_flow_md": None
        }

    if not LLAMA_CLOUD_API_KEY:
        raise ValueError("LLAMA_CLOUD_API_KEY not configured")

    results: dict[str, str | None] = {
        "BS": None,
        "PL": None,
        "Cash Flow": None
    }

    logger.info("Processing %d categories with LlamaParse", len(llamaparse_categories))

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_category = {
            executor.submit(
                _parse_category_worker,
                LLAMA_CLOUD_API_KEY,
                pdf_path,
                category,
                pages
            ): category
            for category, pages in llamaparse_categories.items()
        }

        for future in as_completed(future_to_category):
            category = future_to_category[future]
            try:
                result = future.result()
                if result.get("status") == "success":
                    results[category] = result.get("markdown")
            except Exception as e:
                logger.error("Error getting result for %s: %s", category, e)

    return {
        "company_name": pdf_name,
        "balance_sheet_md": results.get("BS"),
        "profit_loss_md": results.get("PL"),
        "cash_flow_md": results.get("Cash Flow")
    }
