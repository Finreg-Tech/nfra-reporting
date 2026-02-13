import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict
from src.services.rag.retrieval_service import retrieve_rules

logger = logging.getLogger(__name__)

router = APIRouter()

class NFRAQueryRequest(BaseModel):
    document_type: str
    standard_code: str
    standard_number: Optional[int] = None
    section_name: Optional[str] = None
    section_order: Optional[int] = None
    page_number: Optional[int] = None

class NFRAQueryResponse(BaseModel):
    results: List[Dict]
    count: int

@router.post("/NFRA-QUERY", response_model=NFRAQueryResponse)
async def nfra_query(request: NFRAQueryRequest):
    logger.info("Received NFRA-QUERY request: document_type=%s, standard_code=%s", 
                request.document_type, request.standard_code)
    
    if not request.document_type:
        logger.warning("Missing required field: document_type")
        raise HTTPException(
            status_code=400,
            detail="document_type is required"
        )
    
    if not request.standard_code:
        logger.warning("Missing required field: standard_code")
        raise HTTPException(
            status_code=400,
            detail="standard_code is required"
        )
    
    try:
        logger.info("Executing query with filters: standard_number=%s, section_name=%s, section_order=%s, page_number=%s",
                    request.standard_number, request.section_name, request.section_order, request.page_number)
        results = retrieve_rules(
            document_type=request.document_type,
            standard_code=request.standard_code,
            standard_number=request.standard_number,
            section_name=request.section_name,
            section_order=request.section_order,
            page_number=request.page_number
        )
        
        logger.info("Query successful: returned %d results", len(results))
        return NFRAQueryResponse(
            results=results,
            count=len(results)
        )
    except Exception as e:
        logger.error("Query failed: %s", str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Query failed: {str(e)}"
        )
