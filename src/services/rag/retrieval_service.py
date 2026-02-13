import logging
from typing import List, Dict, Optional
from src.services.database.models import query_rules

logger = logging.getLogger(__name__)

def retrieve_rules(
    document_type: str,
    standard_code: str,
    standard_number: Optional[int] = None,
    section_name: Optional[str] = None,
    section_order: Optional[int] = None,
    page_number: Optional[int] = None
) -> List[Dict]:
    logger.info("Retrieving rules for document_type=%s, standard_code=%s", document_type, standard_code)
    results = query_rules(
        document_type=document_type,
        standard_code=standard_code,
        standard_number=standard_number,
        section_name=section_name,
        section_order=section_order,
        page_number=page_number
    )
    logger.info("Retrieved %d rules", len(results))
    return results
