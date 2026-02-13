import os
import logging
from typing import List, Dict, Optional
from dotenv import load_dotenv

from src.services.rag.embedding_service import generate_embedding, generate_embeddings_batch
from src.services.database.models import vector_search, hybrid_search

load_dotenv()

logger = logging.getLogger(__name__)

def semantic_search(
    query: str,
    top_k: int = 5,
    document_type: Optional[str] = None,
    standard_code: Optional[str] = None
) -> List[Dict]:
    logger.info("Performing semantic search: query='%s...'", query[:50])
    
    query_embedding = generate_embedding(query)
    
    results = vector_search(
        query_embedding=query_embedding,
        top_k=top_k,
        document_type=document_type,
        standard_code=standard_code
    )
    
    return results

def rag_search(
    query: str,
    top_k: int = 5,
    document_type: Optional[str] = None,
    use_hybrid: bool = True,
    alpha: float = 0.7
) -> List[Dict]:
    logger.info("Performing RAG search: query='%s...', hybrid=%s", query[:50], use_hybrid)
    
    query_embedding = generate_embedding(query)
    
    if use_hybrid:
        results = hybrid_search(
            query_embedding=query_embedding,
            query_text=query,
            top_k=top_k,
            document_type=document_type,
            alpha=alpha
        )
    else:
        results = vector_search(
            query_embedding=query_embedding,
            top_k=top_k,
            document_type=document_type
        )
    
    return results

class NFRARetriever:
    def __init__(self, document_type: Optional[str] = None):
        self.document_type = document_type
        logger.info("Initialized NFRARetriever for document_type=%s", document_type)
    
    def retrieve(self, query: str, top_k: int = 5, use_hybrid: bool = True) -> List[Dict]:
        return rag_search(
            query=query,
            top_k=top_k,
            document_type=self.document_type,
            use_hybrid=use_hybrid
        )
    
    def retrieve_with_context(self, query: str, top_k: int = 5) -> str:
        results = self.retrieve(query, top_k)
        
        context_parts = []
        for i, result in enumerate(results, 1):
            standard = result.get("standard_code", "Unknown")
            section = result.get("section_name", "Unknown")
            text = result.get("actual_text", result.get("chunk", ""))
            score = result.get("similarity", result.get("score", 0))
            
            context_parts.append(
                f"[{i}] {standard} - {section} (score: {score:.3f}):\n{text}\n"
            )
        
        return "\n---\n".join(context_parts)
