import logging
import fitz
from typing import List

logger = logging.getLogger(__name__)

def extract_text_from_pdf(file_bytes: bytes) -> List[str]:
    logger.info("Extracting text from PDF (%d bytes)", len(file_bytes))
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    pages = []
    for idx, page in enumerate(doc):
        text = page.get_text()
        pages.append(text)
        logger.debug("Extracted page %d: %d characters", idx + 1, len(text))
    doc.close()
    logger.info("Extracted %d pages from PDF", len(pages))
    return pages

def extract_full_text(file_bytes: bytes) -> str:
    pages = extract_text_from_pdf(file_bytes)
    full_text = "\n".join(pages)
    logger.info("Total extracted text: %d characters", len(full_text))
    return full_text
