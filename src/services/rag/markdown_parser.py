import os
import logging
import tempfile
from typing import List, Dict
from llama_parse import LlamaParse
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

parser = LlamaParse(
    api_key=os.getenv("LLAMA_CLOUD_API_KEY"),
    result_type="markdown",
    verbose=False
)

def extract_markdown_from_pdf(file_bytes: bytes) -> str:
    """Extract markdown without page info (legacy support)"""
    pages = extract_markdown_with_pages(file_bytes)
    return "\n\n".join([p["text"] for p in pages])

def extract_markdown_with_pages(file_bytes: bytes) -> List[Dict]:
    """Extract markdown with page numbers from LlamaParse.
    
    Returns:
        List of dicts with 'page_number' and 'text' keys
    """
    logger.info("Converting PDF to Markdown using LlamaParse...")
    logger.info("PDF size: %d bytes", len(file_bytes))
    
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name
    
    try:
        documents = parser.load_data(tmp_path)
        
        pages = []
        for i, doc in enumerate(documents):
            page_num = i + 1
            if hasattr(doc, 'metadata') and doc.metadata:
                page_num = doc.metadata.get('page_number', i + 1) or doc.metadata.get('page', i + 1) or i + 1
            
            pages.append({
                "page_number": page_num,
                "text": doc.text
            })
            logger.debug("Page %d: %d characters", page_num, len(doc.text))
        
        logger.info("Markdown extraction complete: %d pages", len(pages))
        return pages
        
    finally:
        os.unlink(tmp_path)
