import logging
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional
from src.services.rag.ingestion_service import ingest_pdf

logger = logging.getLogger(__name__)

router = APIRouter()

VALID_DOCUMENT_TYPES = ["IndAS", "SEBI", "RBI", "CompanyAct"]

@router.post("/ingest")
async def ingest_document(
    file: UploadFile = File(...),
    rules: str = Form(...),
    use_llm: Optional[bool] = Form(False)
):
    logger.info("Received ingestion request: file=%s, rules=%s, use_llm=%s", file.filename, rules, use_llm)
    
    if rules not in VALID_DOCUMENT_TYPES:
        logger.warning("Invalid document type: %s", rules)
        raise HTTPException(
            status_code=400,
            detail=f"Invalid document type. Must be one of: {VALID_DOCUMENT_TYPES}"
        )
    
    if not file.filename.endswith(".pdf"):
        logger.warning("Invalid file type: %s", file.filename)
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported"
        )
    
    file_bytes = await file.read()
    logger.info("Read file: %d bytes", len(file_bytes))
    
    try:
        sections_inserted = ingest_pdf(file_bytes, rules, use_llm=use_llm)
        logger.info("Ingestion successful: %d sections inserted", sections_inserted)
        return {
            "message": "Ingestion successful",
            "sections_inserted": sections_inserted,
            "parsing_method": "LlamaParse + GPT-4o-mini" if use_llm else "Regex-based"
        }
    except Exception as e:
        logger.error("Ingestion failed: %s", str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Ingestion failed: {str(e)}"
        )
