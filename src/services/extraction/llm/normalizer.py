import re

from config import LIGATURES


def normalize_text(text: str) -> str:
    text = text.lower()
    for ligature, replacement in LIGATURES.items():
        text = text.replace(ligature, replacement)
    return re.sub(r"\s+", " ", text).strip()


def normalize_category(category: str, default: str = "Others") -> str:
    cat = category.lower().strip()
    if "balance" in cat or cat == "bs":
        return "BS"
    if "profit" in cat or "loss" in cat or "income" in cat or cat in ("pl", "p&l"):
        return "PL"
    if "cash" in cat:
        return "Cash Flow"
    if "note" in cat:
        return "Notes"
    return default


def sanitize_name(name: str) -> str:
    return "".join(c if c.isalnum() or c in (" ", "-", "_") else "_" for c in name).strip()
