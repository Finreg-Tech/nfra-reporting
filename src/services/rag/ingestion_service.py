import logging
from typing import List, Dict
from src.services.rag.pdf_parser import extract_full_text
from src.services.rag.section_splitter import parse_document
from src.services.rag.llm_parser import parse_document_with_llm
from src.services.rag.markdown_parser import extract_markdown_with_pages
from src.services.rag.embedding_service import generate_embeddings_batch
from src.services.database.models import insert_rules_batch

logger = logging.getLogger(__name__)

def ingest_pdf(file_bytes: bytes, document_type: str, use_llm: bool = False) -> int:
    logger.info("Starting PDF ingestion for document_type: %s", document_type)
    logger.info("PDF size: %d bytes", len(file_bytes))
    logger.info("Parsing method: %s", "LlamaParse + GPT-4o-mini" if use_llm else "Regex-based")
    
    if use_llm:
        logger.info("Step 1: Converting PDF to Markdown with page numbers using LlamaParse...")
        pages = extract_markdown_with_pages(file_bytes)
        logger.info("Extracted %d pages from PDF", len(pages))
        
        logger.info("Step 2: Extracting structured data with GPT-4o-mini (with page tracking)...")
        markdown_text = "\n\n".join([p["text"] for p in pages])
        parsed_sections = parse_document_with_llm(markdown_text, document_type, pages=pages)
    else:
        logger.info("Step 1: Extracting text from PDF...")
        full_text = extract_full_text(file_bytes)
        
        logger.info("Step 2: Parsing document into sections...")
        parsed_sections = parse_document(full_text, document_type)
    
    logger.info("Step 3: Generating embeddings for %d sections...", len(parsed_sections))
    texts = [section.get("actual_text", "") or section.get("chunk", "") for section in parsed_sections]
    embeddings = generate_embeddings_batch(texts)
    
    for i, section in enumerate(parsed_sections):
        section["embedding"] = embeddings[i]
    
    logger.info("Step 4: Inserting %d sections with embeddings into database...", len(parsed_sections))
    count = insert_rules_batch(parsed_sections)
    
    logger.info("Ingestion complete. Inserted %d sections with vector embeddings.", count)
    return count
