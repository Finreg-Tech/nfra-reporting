import fitz

from config import HEADER_KEYWORDS
from src.services.extraction.llm.normalizer import normalize_text


def extract_header_text(page, header_ratio: float = 0.15) -> str:
    rect = page.rect
    header_rect = fitz.Rect(rect.x0, rect.y0, rect.x1, rect.y0 + rect.height * header_ratio)
    return normalize_text(page.get_text(clip=header_rect))


def is_notes_page(header_text: str) -> bool:
    return header_text.startswith("notes")


def key_matching(pdf_path: str, category_pages: dict[str, list[int]]) -> dict[str, list[int]]:
    doc = fitz.open(pdf_path)
    filtered: dict[str, list[int]] = {}

    for category, pages in category_pages.items():
        if category not in ("BS", "PL", "Cash Flow"):
            filtered[category] = pages
            continue

        keywords = HEADER_KEYWORDS.get(category, [])
        matched = []

        for page_num in pages:
            header = extract_header_text(doc[page_num])
            if is_notes_page(header):
                continue
            if any(kw in header for kw in keywords):
                matched.append(page_num)

        filtered[category] = matched

    doc.close()
    return filtered


def create_category_pdf(pdf_path: str, page_indices: list[int]) -> bytes:
    doc = fitz.open(pdf_path)
    new_doc = fitz.open()
    for p in page_indices:
        new_doc.insert_pdf(doc, from_page=p, to_page=p)
    pdf_bytes = new_doc.tobytes()
    new_doc.close()
    doc.close()
    return pdf_bytes
