"""
Accountant Agent - Ind AS compliance validation using Knowledge Graph.
"""
import logging
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any

from src.core.state import AgentState
from resources.prompts.prompts import ACCOUNTANT_COMPLIANCE_PROMPT
from src.services.rag.retrieval_service import retrieve_rules
from config import KNOWLEDGE_GRAPH_PATH

logger = logging.getLogger(__name__)

# Load Knowledge Graph
try:
    with open(KNOWLEDGE_GRAPH_PATH, "r") as f:
        KNOWLEDGE_GRAPH = json.load(f)
except Exception as e:
    logger.error("Failed to load Knowledge Graph: %s", str(e))
    KNOWLEDGE_GRAPH = {}

_llm = None

def get_llm():
    global _llm
    if _llm is None:
        try:
            from langchain_openai import ChatOpenAI
            from config import OPENAI_API_KEY, OPENAI_MODEL
            _llm = ChatOpenAI(model=OPENAI_MODEL, temperature=0, api_key=OPENAI_API_KEY)
        except ImportError:
            _llm = None
    return _llm

def extract_note_text(extracted_text: str, note_reference: str) -> Optional[str]:
    if not extracted_text or not note_reference: return None
    note_ref = note_reference.strip().lower().replace("note ", "")
    # Robust patterns for Note extraction
    patterns = [
        rf"(?:^|\n)(?:##?\s*)?(?:Note\s+)?{re.escape(note_ref)}[\.\:\s](.+?)(?=\n(?:##?\s*)?(?:Note\s+)?\d|\Z)",
        rf"(?:^|\n){re.escape(note_ref)}[\.\:\s](.+?)(?=\n\d+[\.\:\s]|\Z)",
    ]
    for pattern in patterns:
        match = re.search(pattern, extracted_text, re.IGNORECASE | re.DOTALL)
        if match: return match.group(1).strip()[:3000]
    return None

def llm_compliance_check(row_label, row_data, rule_context, note_text, standard_code):
    """
    Perform LLM-based compliance check for a line item against Ind AS rules.
    
    Returns dict with: status, evidence, reasoning
    """
    note_reference = row_data.get('note_reference')
    
    # Handle missing notes context - if note_reference exists but note_text is None
    if note_reference and note_text is None:
        return {
            "status": "FAIL",
            "evidence": f"[MISSING NOTES CONTEXT] Validation could not be completed because "
                       f"the text for Note {note_reference} was not found in the ingested "
                       f"statements (BS, PL, CF only). The disclosure requirements of {standard_code} "
                       f"cannot be verified without the corresponding note text.",
            "reasoning": f"Note {note_reference} is referenced but its text content was not "
                        f"extracted from the financial statements. This is typically because "
                        f"Notes to Accounts are not included in the primary statement sections.",
            "is_missing_notes": True,
            "note_reference": note_reference
        }
    
    financial_context = f"""
    Line Item: {row_data.get('raw_label', row_label)}
    Value (Current Year): {row_data.get('values', {}).get('current_year', 'N/A')}
    Value (Previous Year): {row_data.get('values', {}).get('previous_year', 'N/A')}
    Note Reference: {note_reference or 'None provided'}
    Note Text: {note_text if note_text else 'Not available'}
    """
    
    llm = get_llm()
    if not llm:
        return {
            "status": "SKIPPED",
            "evidence": "LLM not available for compliance check.",
            "reasoning": "The compliance validation requires an LLM but none was configured."
        }
    
    chain = ACCOUNTANT_COMPLIANCE_PROMPT | llm
    try:
        response = chain.invoke({
            "retrieved_ind_as_rule": f"[{standard_code}]\n{rule_context}",
            "extracted_financial_data": financial_context
        })
        
        content = response.content.strip()
        
        # Try to parse JSON response
        try:
            # Find JSON in response
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                parsed = json.loads(json_match.group())
                status = parsed.get("status", "PASS").upper()
                finding = parsed.get("finding", "")
                details = parsed.get("details", "")
                reasoning = parsed.get("reasoning", "")
                recommendation = parsed.get("recommendation", "")
                
                # Build comprehensive evidence
                evidence_parts = []
                if finding:
                    evidence_parts.append(f"Finding: {finding}")
                if details:
                    evidence_parts.append(f"Details: {details}")
                if recommendation and status == "FAIL":
                    evidence_parts.append(f"Recommendation: {recommendation}")
                
                return {
                    "status": status if status in ["PASS", "FAIL", "N/A"] else "PASS",
                    "evidence": " | ".join(evidence_parts) if evidence_parts else content[:200],
                    "reasoning": reasoning or finding or "See evidence for details."
                }
        except json.JSONDecodeError:
            pass
        
        # Fallback: Simple text parsing
        if "FAIL" in content.upper():
            return {
                "status": "FAIL",
                "evidence": content[:300],
                "reasoning": "LLM determined non-compliance. See evidence for details."
            }
        
        return {
            "status": "PASS",
            "evidence": content[:300] if content else "Compliance check passed.",
            "reasoning": "LLM determined compliance with the standard."
        }
        
    except Exception as e:
        logger.error("LLM compliance check failed: %s", str(e))
        return {
            "status": "ERROR",
            "evidence": f"Compliance check error: {str(e)[:100]}",
            "reasoning": "An error occurred during the LLM compliance validation."
        }

def accountant_node(state: AgentState) -> AgentState:
    print("--- ACCOUNTANT NODE ---")
    bs_data = state.get("extracted_data", {}).get("balance_sheet", {})
    rows = bs_data.get("rows", [])
    full_text = state.get("markdown_content", {}).get("full_text", "")
    
    # Get Mapping from JSON
    bs_mapping = KNOWLEDGE_GRAPH.get("financial_statement_mapping", {}).get("balance_sheet", {})
    compliance_flags = []
    
    for row in rows:
        label = row.get("normalized_label")
        if label not in bs_mapping: continue
        
        rule_info = bs_mapping[label]
        standard_code = rule_info["standard_code"] # Must be "Ind AS 16" etc.
        
        # Exact DB Retrieval
        print(f"Retrieving rules for {standard_code}...")
        rules = retrieve_rules(document_type="IndAS", standard_code=standard_code)
        
        if not rules:
            logger.warning(f"No rules found for {standard_code}")
            continue
            
        rule_context = "\n".join([r["actual_text"] for r in rules[:10]])
        note_text = extract_note_text(full_text, row.get("note_reference"))
        
        result = llm_compliance_check(label, row, rule_context, note_text, standard_code)
        
        if result["status"] == "FAIL":
            compliance_flags.append({
                "rule_id": f"{standard_code}_{label}",
                "item": label,
                "description": row.get("raw_label", label),
                "status": "FAIL",
                "severity": "critical" if result.get("is_missing_notes") else "high",
                "evidence": result["evidence"],
                "reasoning": result.get("reasoning", ""),
                "is_missing_notes": result.get("is_missing_notes", False),
                "note_reference": result.get("note_reference")
            })
        elif result["status"] == "PASS":
            # Log passed items for debugging
            logger.debug(f"Compliance PASS: {standard_code}_{label} - {result.get('reasoning', '')}")

    # Update State
    if "validation_results" not in state: state["validation_results"] = {}
    state["validation_results"]["compliance_flags"] = compliance_flags
    return state