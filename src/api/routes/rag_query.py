import logging
from typing import Optional, List
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter()

class RAGQueryRequest(BaseModel):
    query: str = Field(..., description="The search query text")
    top_k: int = Field(default=5, ge=1, le=50, description="Number of results to return")
    document_type: Optional[str] = Field(default=None, description="Filter by document type")
    use_hybrid: bool = Field(default=True, description="Use hybrid search (vector + text)")
    alpha: float = Field(default=0.7, ge=0, le=1, description="Weight for vector vs text score (0=text only, 1=vector only)")

class RAGResult(BaseModel):
    id: int
    document_type: Optional[str]
    standard_code: Optional[str]
    standard_number: Optional[str]
    standard_name: Optional[str]
    section_name: Optional[str]
    page_number: Optional[int]
    actual_text: str
    score: float

class RAGQueryResponse(BaseModel):
    query: str
    results: List[RAGResult]
    total_results: int

@router.post("/rag-query", response_model=RAGQueryResponse)
async def rag_query(request: RAGQueryRequest):
    logger.info("RAG query received: '%s...'", request.query[:50])
    logger.info("Parameters: top_k=%d, document_type=%s, hybrid=%s, alpha=%.2f",
                request.top_k, request.document_type, request.use_hybrid, request.alpha)
    
    try:
        from src.services.rag.rag_service import rag_search
        
        results = rag_search(
            query=request.query,
            top_k=request.top_k,
            document_type=request.document_type,
            use_hybrid=request.use_hybrid,
            alpha=request.alpha
        )
        
        formatted_results = []
        for r in results:
            formatted_results.append(RAGResult(
                id=r.get("id", 0),
                document_type=r.get("document_type"),
                standard_code=r.get("standard_code"),
                standard_number=r.get("standard_number"),
                standard_name=r.get("standard_name"),
                section_name=r.get("section_name"),
                page_number=r.get("page_number"),
                actual_text=r.get("actual_text", r.get("chunk", "")),
                score=r.get("similarity", r.get("score", 0))
            ))
        
        logger.info("RAG query returned %d results", len(formatted_results))
        
        return RAGQueryResponse(
            query=request.query,
            results=formatted_results,
            total_results=len(formatted_results)
        )
        
    except Exception as e:
        logger.error("RAG query failed: %s", str(e))
        raise HTTPException(status_code=500, detail=f"RAG query failed: {str(e)}")

@router.get("/rag-search")
async def rag_search_get(
    query: str = Query(..., description="Search query text"),
    top_k: int = Query(default=5, ge=1, le=50, description="Number of results"),
    document_type: Optional[str] = Query(default=None, description="Filter by document type"),
    use_hybrid: bool = Query(default=True, description="Use hybrid search")
):
    logger.info("RAG GET search: '%s...'", query[:50])
    
    request = RAGQueryRequest(
        query=query,
        top_k=top_k,
        document_type=document_type,
        use_hybrid=use_hybrid
    )
    return await rag_query(request)

@router.post("/semantic-search")
async def semantic_search_endpoint(request: RAGQueryRequest):
    logger.info("Semantic search received: '%s...'", request.query[:50])
    
    try:
        from src.services.rag.rag_service import semantic_search
        
        results = semantic_search(
            query=request.query,
            top_k=request.top_k,
            document_type=request.document_type
        )
        
        formatted_results = []
        for r in results:
            formatted_results.append(RAGResult(
                id=r.get("id", 0),
                document_type=r.get("document_type"),
                standard_code=r.get("standard_code"),
                standard_number=r.get("standard_number"),
                standard_name=r.get("standard_name"),
                section_name=r.get("section_name"),
                page_number=r.get("page_number"),
                actual_text=r.get("actual_text", r.get("chunk", "")),
                score=r.get("similarity", 0)
            ))
        
        logger.info("Semantic search returned %d results", len(formatted_results))
        
        return RAGQueryResponse(
            query=request.query,
            results=formatted_results,
            total_results=len(formatted_results)
        )
        
    except Exception as e:
        logger.error("Semantic search failed: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Semantic search failed: {str(e)}")
