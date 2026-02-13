import logging
import re
import fitz
from typing import Dict, Optional, Any, List
from src.core.state import AgentState, MetadataState
from src.services.extraction.llm.extractor import extract_financial_markdown
from src.services.extraction.llm.pipeline import process_company

logger = logging.getLogger(__name__)


# =============================================================================
# Schema Validation
# =============================================================================

REQUIRED_STATEMENT_KEYS = ["rows", "totals", "metadata"]
REQUIRED_BS_TOTALS_KEYS = ["total_assets", "total_equity_and_liabilities"]
REQUIRED_PL_TOTALS_KEYS = ["profit_after_tax"]
REQUIRED_CF_TOTALS_KEYS = ["closing_cash_balance"]


class SchemaValidationError(ValueError):
    """Raised when extracted data doesn't match expected schema."""
    pass


def validate_statement_schema(
    statement_data: Optional[Dict[str, Any]],
    statement_type: str,
    required_totals: List[str]
) -> List[str]:
    """
    Validate that a financial statement matches the expected schema.
    
    Returns list of validation errors (empty if valid).
    """
    errors = []
    
    if statement_data is None:
        return errors  # Optional statement, no validation needed
    
    if not isinstance(statement_data, dict):
        errors.append(f"{statement_type}: Expected dict, got {type(statement_data).__name__}")
        return errors
    
    # Check required top-level keys
    for key in REQUIRED_STATEMENT_KEYS:
        if key not in statement_data:
            errors.append(f"{statement_type}: Missing required key '{key}'")
    
    # Validate 'rows' is a list
    rows = statement_data.get("rows")
    if rows is not None and not isinstance(rows, list):
        errors.append(f"{statement_type}: 'rows' must be a list, got {type(rows).__name__}")
    elif rows:
        # Validate first row has expected structure
        first_row = rows[0]
        if not isinstance(first_row, dict):
            errors.append(f"{statement_type}: Row items must be dicts")
        elif "values" not in first_row:
            errors.append(f"{statement_type}: Row missing 'values' key")
        elif not isinstance(first_row.get("values"), dict):
            errors.append(f"{statement_type}: Row 'values' must be a dict")
    
    # Validate 'totals' structure
    totals = statement_data.get("totals")
    if totals is not None:
        if not isinstance(totals, dict):
            errors.append(f"{statement_type}: 'totals' must be a dict, got {type(totals).__name__}")
        else:
            # Check required totals keys
            for key in required_totals:
                if key not in totals:
                    errors.append(f"{statement_type}: 'totals' missing required key '{key}'")
                else:
                    # Validate nested structure: totals[key] should have current_year/previous_year
                    total_value = totals[key]
                    if isinstance(total_value, dict):
                        if "current_year" not in total_value:
                            errors.append(f"{statement_type}: totals['{key}'] missing 'current_year'")
                    elif not isinstance(total_value, (int, float)):
                        errors.append(f"{statement_type}: totals['{key}'] has invalid type")
    
    # Validate 'metadata' structure
    metadata = statement_data.get("metadata")
    if metadata is not None and not isinstance(metadata, dict):
        errors.append(f"{statement_type}: 'metadata' must be a dict")
    
    return errors


def validate_extraction_schema(extracted_data: Dict[str, Any]) -> None:
    """
    Validate the full extracted data matches expected schema.
    
    Raises SchemaValidationError if validation fails.
    """
    all_errors = []
    
    # Validate Balance Sheet (mandatory)
    bs_data = extracted_data.get("balance_sheet")
    if bs_data is None:
        all_errors.append("balance_sheet: Data is missing (required)")
    else:
        bs_errors = validate_statement_schema(bs_data, "balance_sheet", REQUIRED_BS_TOTALS_KEYS)
        all_errors.extend(bs_errors)
    
    # Validate Profit & Loss (optional but validate if present)
    pl_data = extracted_data.get("profit_loss")
    if pl_data is not None:
        pl_errors = validate_statement_schema(pl_data, "profit_loss", REQUIRED_PL_TOTALS_KEYS)
        all_errors.extend(pl_errors)
    
    # Validate Cash Flow (optional but validate if present)
    cf_data = extracted_data.get("cash_flow")
    if cf_data is not None:
        cf_errors = validate_statement_schema(cf_data, "cash_flow", REQUIRED_CF_TOTALS_KEYS)
        all_errors.extend(cf_errors)
    
    if all_errors:
        error_msg = "Extraction Schema Mismatch:\n" + "\n".join(f"  - {e}" for e in all_errors)
        logger.error("Gatekeeper: %s", error_msg)
        raise SchemaValidationError(error_msg)

def extract_metadata_from_pdf(file_path: str) -> MetadataState:
    try:
        doc = fitz.open(file_path)
    except Exception as e:
        raise ValueError(f"Failed to open PDF: {str(e)}")
    
    full_text = ""
    for page_num in range(min(5, len(doc))):
        full_text += doc[page_num].get_text()
    doc.close()
    
    metadata: MetadataState = {
        "cin": None,
        "fy": None,
        "company_name": None,
        "report_type": None
    }
    
    cin_pattern = r'[A-Z]{1}\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}'
    cin_match = re.search(cin_pattern, full_text)
    if cin_match:
        metadata["cin"] = cin_match.group()
    
    fy_patterns = [
        r'(?:FY|Financial Year|Year ended|For the year ended)[:\s]*(\d{4}[-–]\d{2,4})',
        r'(\d{4}[-–]\d{2,4})',
        r'(?:March|Mar)\s*(\d{4})'
    ]
    for pattern in fy_patterns:
        fy_match = re.search(pattern, full_text, re.IGNORECASE)
        if fy_match:
            metadata["fy"] = fy_match.group(1)
            break
    
    if "annual report" in full_text.lower():
        metadata["report_type"] = "Annual Report"
    elif "quarterly" in full_text.lower():
        metadata["report_type"] = "Quarterly Report"
    elif "half year" in full_text.lower() or "half-year" in full_text.lower():
        metadata["report_type"] = "Half-Yearly Report"
    else:
        metadata["report_type"] = "Financial Statement"
    
    return metadata

async def gatekeeper_node(state: AgentState) -> AgentState:
    print("--- GATEKEEPER NODE ---")
    logger.info("Gatekeeper: Starting extraction for %s", state["file_path"])
    
    file_path = state["file_path"]
    
    if not file_path:
        raise ValueError("Gatekeeper: No file path provided in state")
    
    logger.info("Gatekeeper: Step 1 - Extracting metadata from PDF")
    metadata = extract_metadata_from_pdf(file_path)
    logger.info("Gatekeeper: Metadata extracted - CIN: %s, FY: %s", metadata.get("cin"), metadata.get("fy"))
    
    logger.info("Gatekeeper: Step 2 - Parsing PDF to extract Markdown")
    markdown_data = extract_financial_markdown(file_path)
    
    if not markdown_data:
        raise ValueError("Gatekeeper: Failed to extract markdown from PDF")
    
    company_name = markdown_data.get("company_name", "unknown")
    if metadata.get("company_name") is None:
        metadata["company_name"] = company_name
    
    state["metadata"] = metadata
    
    bs_md = markdown_data.get("balance_sheet_md", "")
    pl_md = markdown_data.get("profit_loss_md", "")
    cf_md = markdown_data.get("cash_flow_md", "")
    notes_md = markdown_data.get("notes_md", "")
    
    if not any([bs_md, pl_md, cf_md]):
        raise ValueError("Gatekeeper: No financial statements found in PDF")
    
    # ------------------------------------
    # Preserve raw markdown for downstream agents (Accountant, Auditor)
    # ------------------------------------
    full_text_parts = []
    if bs_md:
        full_text_parts.append(f"=== BALANCE SHEET ===\n{bs_md}")
    if pl_md:
        full_text_parts.append(f"=== PROFIT & LOSS ===\n{pl_md}")
    if cf_md:
        full_text_parts.append(f"=== CASH FLOW ===\n{cf_md}")
    if notes_md:
        full_text_parts.append(f"=== NOTES TO ACCOUNTS ===\n{notes_md}")
    
    state["markdown_content"] = {
        "balance_sheet": bs_md or "",
        "profit_loss": pl_md or "",
        "cash_flow": cf_md or "",
        "notes": notes_md or "",
        "full_text": "\n\n".join(full_text_parts)
    }
    logger.info("Gatekeeper: Preserved %d chars of markdown for downstream agents", 
                len(state["markdown_content"]["full_text"]))
    
    logger.info("Gatekeeper: Step 3 - Processing markdown with LLM pipeline")
    
    result = await process_company(company_name, bs_md, pl_md, cf_md)
    
    if result.get("errors"):
        logger.warning("Gatekeeper: Extraction completed with errors - %s", result["errors"])
    
    # ------------------------------------
    # Step 4: Schema Validation
    # ------------------------------------
    logger.info("Gatekeeper: Step 4 - Validating extraction schema")
    
    extracted_json = {
        "balance_sheet": result.get("balance_sheet"),
        "profit_loss": result.get("profit_and_loss"),
        "cash_flow": result.get("cash_flow")
    }
    
    # Validate schema before passing to downstream agents
    # Raises SchemaValidationError if LLM hallucinated bad structure
    try:
        validate_extraction_schema(extracted_json)
        logger.info("Gatekeeper: Schema validation PASSED")
    except SchemaValidationError as e:
        logger.error("Gatekeeper: Schema validation FAILED - %s", str(e))
        # Do NOT pass bad data to Quant agent
        state["processing_status"] = "extraction_failed"
        state["extracted_data"] = {}
        raise  # Re-raise to halt workflow
    
    # Only update state if validation passes
    state["extracted_data"] = extracted_json
    
    state["processing_status"] = "extracted"
    logger.info("Gatekeeper: Extraction complete - BS: %s, PL: %s, CF: %s",
                "OK" if result.get("balance_sheet") else "MISSING",
                "OK" if result.get("profit_and_loss") else "MISSING",
                "OK" if result.get("cash_flow") else "MISSING")
    
    return state
