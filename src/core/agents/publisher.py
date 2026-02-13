"""
Publisher Agent - Final report generation and file output.

NO LLM calls - pure Python report assembly and formatting.
Generates professional Markdown compliance reports.
"""

import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple

from src.core.state import AgentState
from config import KNOWLEDGE_GRAPH_PATH

logger = logging.getLogger(__name__)

# Report output directory
REPORT_DIR = Path("REPORT")

# KNOWLEDGE_GRAPH_PATH is now imported from config


# =============================================================================
# Knowledge Graph Utilities
# =============================================================================

def load_knowledge_graph() -> Dict[str, Any]:
    """Load the knowledge graph mapping line items to Ind AS standards."""
    try:
        with open(KNOWLEDGE_GRAPH_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("Failed to load knowledge graph: %s", e)
        return {}


def get_all_mapped_items(knowledge_graph: Dict) -> Dict[str, Tuple[str, str]]:
    """
    Extract all mapped line items from knowledge graph.
    
    Returns: Dict mapping normalized_label -> (standard_code, standard_name)
    """
    mapped_items = {}
    
    fsm = knowledge_graph.get("financial_statement_mapping", {})
    
    for statement_type in ["balance_sheet", "profit_and_loss", "notes_to_accounts"]:
        statement_items = fsm.get(statement_type, {})
        for item_key, item_data in statement_items.items():
            standard_code = item_data.get("standard_code", "N/A")
            standard_name = item_data.get("standard_name", "N/A")
            mapped_items[item_key] = (standard_code, standard_name)
    
    return mapped_items


def identify_passed_validations(
    extracted_data: Dict,
    compliance_flags: List[Dict],
    knowledge_graph: Dict
) -> List[Dict[str, str]]:
    """
    Identify line items that exist in the Knowledge Graph but passed validation.
    
    Compares extracted data rows against compliance_flags to find items
    that were validated but did NOT generate flags (i.e., passed).
    
    Returns: List of dicts with {line_item, standard_code, standard_name}
    """
    passed_items = []
    
    # Get all mapped items from knowledge graph
    mapped_items = get_all_mapped_items(knowledge_graph)
    
    # Get set of flagged item labels (normalized)
    flagged_labels: Set[str] = set()
    for flag in compliance_flags:
        # Extract the item being flagged
        item = flag.get("item", "")
        rule_id = flag.get("rule_id", "")
        description = flag.get("description", "")
        
        # Normalize and add to flagged set
        if item:
            flagged_labels.add(item.lower().replace(" ", "_"))
        # Also extract from description if it mentions specific items
        for key in mapped_items.keys():
            readable = key.replace("_", " ")
            if readable in description.lower() or key in description.lower():
                flagged_labels.add(key)
    
    # Check extracted data rows against mapped items
    for statement_key in ["balance_sheet", "profit_loss", "cash_flow"]:
        statement_data = extracted_data.get(statement_key)
        if not statement_data:
            continue
        
        rows = statement_data.get("rows", [])
        for row in rows:
            normalized_label = row.get("normalized_label", "")
            raw_label = row.get("raw_label", "")
            
            if not normalized_label:
                continue
            
            # Check if this item is in the knowledge graph
            if normalized_label in mapped_items:
                # Check if it was NOT flagged (i.e., passed)
                if normalized_label not in flagged_labels:
                    standard_code, standard_name = mapped_items[normalized_label]
                    passed_items.append({
                        "line_item": raw_label or normalized_label.replace("_", " ").title(),
                        "normalized": normalized_label,
                        "standard_code": standard_code,
                        "standard_name": standard_name
                    })
    
    # Deduplicate by normalized label
    seen = set()
    unique_passed = []
    for item in passed_items:
        if item["normalized"] not in seen:
            seen.add(item["normalized"])
            unique_passed.append(item)
    
    return unique_passed


def check_missing_notes_context(flag: Dict, extracted_data: Dict) -> Tuple[bool, Optional[str]]:
    """
    Check if a compliance failure is due to missing notes context.
    
    Returns: (is_missing_notes, note_reference)
    """
    evidence = flag.get("evidence", "") or flag.get("issue", "") or ""
    status = flag.get("status", "")
    item = flag.get("item", "")
    
    # Look for indicators of missing notes
    missing_indicators = [
        "note.*not found",
        "missing.*note",
        "no note reference",
        "note text.*empty",
        "note.*unavailable",
        "could not.*note",
        "note reference.*missing"
    ]
    
    evidence_lower = evidence.lower()
    is_missing = any(re.search(pattern, evidence_lower) for pattern in missing_indicators)
    
    # If not explicitly missing, check if the item has a note_reference in extracted data
    note_ref = None
    if item and not is_missing:
        # Search for the item in extracted data
        for statement_key in ["balance_sheet", "profit_loss", "cash_flow"]:
            statement_data = extracted_data.get(statement_key)
            if not statement_data:
                continue
            
            rows = statement_data.get("rows", [])
            for row in rows:
                normalized_label = row.get("normalized_label", "")
                if normalized_label == item or item.lower().replace(" ", "_") == normalized_label:
                    note_ref = row.get("note_reference")
                    # If there's a note_reference but the validation failed, might be missing context
                    if note_ref and status == "FAIL":
                        # Check if evidence suggests the note wasn't found
                        if not evidence or "pass" not in evidence_lower:
                            is_missing = True
                    break
    
    return is_missing, note_ref


# =============================================================================
# Scoring Functions
# =============================================================================

def calculate_overall_score(validation_results: Dict) -> Dict:
    """Calculate compliance score based on validation results."""
    quant_errors = validation_results.get("quant_errors", [])
    compliance_flags = validation_results.get("compliance_flags", [])
    risk_alerts = validation_results.get("risk_alerts", [])
    
    base_score = 100
    
    # Deduct for math errors
    for error in quant_errors:
        if error.get("passed") == False or error.get("status") == "FAIL":
            base_score -= 15
    
    # Deduct for compliance flags
    for flag in compliance_flags:
        severity = flag.get("severity", "")
        status = flag.get("status", "")
        if severity == "critical" or status == "FAIL":
            base_score -= 15
        elif severity == "warning" or status == "WARNING":
            base_score -= 10
        elif status == "REVIEW":
            base_score -= 5
    
    # Deduct for risk alerts
    for alert in risk_alerts:
        severity = str(alert.get("severity", "")).upper()
        if severity == "CRITICAL":
            base_score -= 20
        elif severity == "HIGH":
            base_score -= 10
        elif severity == "MEDIUM":
            base_score -= 5
    
    score = max(0, min(100, base_score))
    
    if score >= 80:
        grade = "A"
        status = "COMPLIANT"
    elif score >= 60:
        grade = "B"
        status = "COMPLIANT_WITH_OBSERVATIONS"
    elif score >= 40:
        grade = "C"
        status = "NEEDS_REVIEW"
    else:
        grade = "D"
        status = "NON_COMPLIANT"
    
    return {
        "score": score,
        "grade": grade,
        "status": status
    }


def generate_summary(validation_results: Dict, extracted_data: Optional[Dict] = None) -> Dict:
    """
    Generate summary of critical issues and warnings.
    
    Attributes failures to missing notes context when applicable.
    Returns structured data with explanations for each issue.
    """
    quant_errors = validation_results.get("quant_errors", [])
    compliance_flags = validation_results.get("compliance_flags", [])
    risk_alerts = validation_results.get("risk_alerts", [])
    
    extracted_data = extracted_data or {}
    
    critical_issues = []
    warnings = []
    
    for error in quant_errors:
        if error.get("passed") == False or error.get("status") == "FAIL":
            msg = error.get("message") or error.get("details") or str(error.get("check_name", "Unknown"))
            critical_issues.append({
                "text": f"Mathematical Error: {msg[:100]}",
                "sub_reason": None
            })
    
    for flag in compliance_flags:
        severity = flag.get("severity", "")
        desc = flag.get("description") or flag.get("item") or flag.get("rule_id", "")
        evidence = flag.get("evidence") or flag.get("issue") or ""
        reasoning = flag.get("reasoning", "")
        rule_id = flag.get("rule_id", "N/A")
        
        # Check if failure is due to missing notes context
        is_missing_notes = flag.get("is_missing_notes", False)
        note_ref = flag.get("note_reference")
        
        if not is_missing_notes:
            is_missing_notes, note_ref = check_missing_notes_context(flag, extracted_data)
        
        if severity == "critical" or flag.get("status") == "FAIL":
            if is_missing_notes:
                if note_ref:
                    issue_text = f"Rule Failure ({rule_id}): {desc[:50]}"
                    sub_reason = f"Reason: Incomplete data ingestion - Note {note_ref} text not found in BS/PL/CF statements."
                else:
                    issue_text = f"Rule Failure ({rule_id}): {desc[:50]}"
                    sub_reason = "Reason: Incomplete data ingestion (Notes to Accounts missing)."
                
                critical_issues.append({
                    "text": issue_text,
                    "sub_reason": sub_reason,
                    "is_missing_notes": True
                })
            else:
                # Include reasoning in the issue description
                issue_text = f"Compliance Issue ({rule_id}): {desc[:60]}"
                sub_reason = f"Finding: {reasoning[:80]}" if reasoning else None
                
                critical_issues.append({
                    "text": issue_text,
                    "sub_reason": sub_reason,
                    "is_missing_notes": False
                })
        else:
            warnings.append({
                "text": f"Compliance Review: {desc[:80]}",
                "sub_reason": f"Details: {reasoning[:60]}" if reasoning else None
            })
    
    for alert in risk_alerts:
        severity = str(alert.get("severity", "")).upper()
        risk_type = alert.get("risk_type", "Unknown Risk")
        details = alert.get("details") or alert.get("analysis") or alert.get("message") or ""
        
        if severity in ["CRITICAL", "HIGH"]:
            critical_issues.append({
                "text": f"{risk_type}: {details[:80]}",
                "sub_reason": None
            })
        else:
            warnings.append({
                "text": f"{risk_type}: {details[:80]}",
                "sub_reason": None
            })
    
    return {
        "critical_issues_count": len(critical_issues),
        "warnings_count": len(warnings),
        "critical_issues": critical_issues,
        "warnings": warnings
    }


# =============================================================================
# Markdown Report Formatting
# =============================================================================

# Expected mathematical checks (for showing all checks even if some weren't run)
EXPECTED_MATH_CHECKS = [
    "accounting_equation",
    "vertical_consistency_assets",
    "vertical_consistency_equity_liabilities",
    "horizontal_consistency",
    "cash_balance_consistency",
    "pat_calculation"
]


def format_report_markdown(
    metadata: Dict,
    extracted_data: Dict,
    validation_results: Dict,
    score_info: Dict,
    summary: Dict,
    report_id: str
) -> str:
    """
    Format the final report as professional Markdown.
    
    Includes:
    - Executive summary with score
    - Successful validations (items that passed)
    - Critical issues with notes attribution
    - Full mathematical validation table
    - Compliance analysis with missing notes context
    """
    lines = []
    
    # Load knowledge graph for passed validations
    knowledge_graph = load_knowledge_graph()
    compliance_flags = validation_results.get("compliance_flags", [])
    
    # Title
    company_name = metadata.get("company_name", "Unknown Company")
    cin = metadata.get("cin", "N/A")
    fy = metadata.get("fy", "N/A")
    
    lines.append(f"# NFRA Compliance Report")
    lines.append(f"## {company_name}")
    lines.append("")
    lines.append(f"**Report ID:** {report_id}")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    
    # Executive Summary
    lines.append("---")
    lines.append("")
    lines.append("## Executive Summary")
    lines.append("")
    
    # Score badge
    score = score_info["score"]
    grade = score_info["grade"]
    status = score_info["status"]
    
    if score >= 80:
        status_emoji = "✅"
    elif score >= 60:
        status_emoji = "⚠️"
    elif score >= 40:
        status_emoji = "🔶"
    else:
        status_emoji = "❌"
    
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| **Overall Score** | {score}/100 |")
    lines.append(f"| **Grade** | {grade} |")
    lines.append(f"| **Status** | {status_emoji} {status.replace('_', ' ')} |")
    lines.append(f"| **Critical Issues** | {summary['critical_issues_count']} |")
    lines.append(f"| **Warnings** | {summary['warnings_count']} |")
    lines.append("")
    
    # Company Details
    lines.append("---")
    lines.append("")
    lines.append("## Company Information")
    lines.append("")
    lines.append(f"| Field | Value |")
    lines.append(f"|-------|-------|")
    lines.append(f"| Company Name | {company_name} |")
    lines.append(f"| CIN | {cin} |")
    lines.append(f"| Financial Year | {fy} |")
    lines.append(f"| Report Type | {metadata.get('report_type', 'N/A')} |")
    lines.append("")
    
    # Data Availability
    lines.append("---")
    lines.append("")
    lines.append("## Financial Statements Analysed")
    lines.append("")
    
    bs_available = "✅ Yes" if extracted_data.get("balance_sheet") else "❌ No"
    pl_available = "✅ Yes" if extracted_data.get("profit_loss") else "❌ No"
    cf_available = "✅ Yes" if extracted_data.get("cash_flow") else "❌ No"
    
    lines.append(f"| Statement | Available |")
    lines.append(f"|-----------|-----------|")
    lines.append(f"| Balance Sheet | {bs_available} |")
    lines.append(f"| Profit & Loss | {pl_available} |")
    lines.append(f"| Cash Flow | {cf_available} |")
    lines.append("")
    
    # Key Financial Metrics (if BS available)
    bs_data = extracted_data.get("balance_sheet")
    if bs_data and bs_data.get("totals"):
        lines.append("---")
        lines.append("")
        lines.append("## Key Financial Metrics")
        lines.append("")
        
        totals = bs_data.get("totals", {})
        
        def get_total_value(key: str) -> str:
            val = totals.get(key, {})
            if isinstance(val, dict):
                cy = val.get("current_year", 0)
                return f"{cy:,.2f}" if cy else "N/A"
            return str(val) if val else "N/A"
        
        lines.append(f"| Metric | Current Year |")
        lines.append(f"|--------|--------------|")
        lines.append(f"| Total Assets | {get_total_value('total_assets')} |")
        lines.append(f"| Total Equity | {get_total_value('total_equity')} |")
        lines.append(f"| Total Liabilities | {get_total_value('total_liabilities')} |")
        lines.append("")
    
    # =========================================================================
    # NEW: Successful Validations Section
    # =========================================================================
    passed_validations = identify_passed_validations(extracted_data, compliance_flags, knowledge_graph)
    
    if passed_validations:
        lines.append("---")
        lines.append("")
        lines.append("## ✅ Successful Validations")
        lines.append("")
        lines.append("The following line items were validated against Ind AS standards and **passed**:")
        lines.append("")
        lines.append(f"| Line Item | Standard | Status |")
        lines.append(f"|-----------|----------|--------|")
        for item in passed_validations:
            line_item = item["line_item"][:35]
            standard = f"{item['standard_code']} - {item['standard_name'][:25]}"
            lines.append(f"| {line_item} | {standard} | ✅ Pass |")
        lines.append("")
        lines.append(f"*{len(passed_validations)} items validated successfully.*")
        lines.append("")
    
    # Critical Issues Section
    if summary["critical_issues"]:
        lines.append("---")
        lines.append("")
        lines.append("## ❌ Critical Issues")
        lines.append("")
        lines.append("The following issues require immediate attention:")
        lines.append("")
        
        # Check if issues marked with missing notes
        missing_notes_issues = [i for i in summary["critical_issues"] if isinstance(i, dict) and i.get("is_missing_notes")]
        if missing_notes_issues:
            lines.append("> **Note:** Some failures may be due to missing notes context in the extracted data.")
            lines.append("")
        
        for issue in summary["critical_issues"]:
            if isinstance(issue, dict):
                # New structured format
                lines.append(f"- {issue.get('text', str(issue))}")
                if issue.get("sub_reason"):
                    lines.append(f"  - *Reason:* {issue['sub_reason']}")
            else:
                # Legacy string format
                lines.append(f"- {issue}")
        lines.append("")
    
    # Warnings Section
    if summary["warnings"]:
        lines.append("---")
        lines.append("")
        lines.append("## ⚠️ Warnings")
        lines.append("")
        lines.append("The following items should be reviewed:")
        lines.append("")
        
        for warning in summary["warnings"]:
            if isinstance(warning, dict):
                lines.append(f"- {warning.get('text', str(warning))}")
                if warning.get("sub_reason"):
                    lines.append(f"  - *Reason:* {warning['sub_reason']}")
            else:
                lines.append(f"- {warning}")
        lines.append("")
    
    # =========================================================================
    # Mathematical Validation - Show ALL expected checks
    # =========================================================================
    quant_errors = validation_results.get("quant_errors", [])
    lines.append("---")
    lines.append("")
    lines.append("## Mathematical Validation (Quant Agent)")
    lines.append("")
    
    # Build lookup for actual results
    actual_checks = {err.get("check_name"): err for err in quant_errors}
    
    lines.append(f"| Check | Status | Details |")
    lines.append(f"|-------|--------|---------|")
    
    # Track counts
    passed_count = 0
    failed_count = 0
    skipped_count = 0
    
    for check_name in EXPECTED_MATH_CHECKS:
        if check_name in actual_checks:
            err = actual_checks[check_name]
            passed = err.get("passed", False)
            msg = err.get("message", "")[:50]
            
            if passed:
                status_cell = "✅ Pass"
                passed_count += 1
            else:
                status_cell = "❌ Fail"
                failed_count += 1
            
            # Clean up check name for display
            display_name = check_name.replace("_", " ").title()
            lines.append(f"| {display_name} | {status_cell} | {msg} |")
        else:
            # Check was not run (data not available)
            display_name = check_name.replace("_", " ").title()
            lines.append(f"| {display_name} | ⏭️ Skipped | Data not available |")
            skipped_count += 1
    
    # Also include any additional checks not in expected list
    for check_name, err in actual_checks.items():
        if check_name not in EXPECTED_MATH_CHECKS:
            passed = err.get("passed", False)
            msg = err.get("message", "")[:50]
            status_cell = "✅ Pass" if passed else "❌ Fail"
            if passed:
                passed_count += 1
            else:
                failed_count += 1
            display_name = check_name.replace("_", " ").title()
            lines.append(f"| {display_name} | {status_cell} | {msg} |")
    
    lines.append("")
    lines.append(f"*Summary: {passed_count} passed, {failed_count} failed, {skipped_count} skipped*")
    lines.append("")
    
    # =========================================================================
    # Compliance Flags - With Missing Notes Attribution and Explanations
    # =========================================================================
    lines.append("---")
    lines.append("")
    lines.append("## Compliance Analysis (Accountant Agent)")
    lines.append("")
    
    if compliance_flags:
        lines.append(f"| Rule ID | Line Item | Status | Explanation |")
        lines.append(f"|---------|-----------|--------|-------------|")
        
        for flag in compliance_flags:
            rule_id = flag.get("rule_id", "N/A")
            item = flag.get("item") or flag.get("description", "N/A")
            item_display = item[:25] if isinstance(item, str) else "N/A"
            status = flag.get("status", "N/A")
            
            # Get explanation from evidence or reasoning
            evidence = flag.get("evidence", "")
            reasoning = flag.get("reasoning", "")
            
            # Check for missing notes context
            is_missing_notes = flag.get("is_missing_notes", False)
            if not is_missing_notes:
                is_missing_notes, _ = check_missing_notes_context(flag, extracted_data)
            
            # Build explanation column
            if is_missing_notes:
                explanation = "⚠️ [MISSING NOTES] " + (reasoning[:60] if reasoning else evidence[:60])
            elif reasoning:
                explanation = reasoning[:80]
            elif evidence:
                explanation = evidence[:80]
            else:
                explanation = "No details provided"
            
            # Escape pipe characters in explanation
            explanation = explanation.replace("|", "\\|").replace("\n", " ")
            
            # Status emoji
            status_display = "❌ FAIL" if status == "FAIL" else ("✅ PASS" if status == "PASS" else status)
            
            lines.append(f"| {rule_id[:25]} | {item_display} | {status_display} | {explanation} |")
        
        lines.append("")
        
        # Detailed findings section for failed items
        failed_flags = [f for f in compliance_flags if f.get("status") == "FAIL"]
        if failed_flags:
            lines.append("### Detailed Findings")
            lines.append("")
            for i, flag in enumerate(failed_flags, 1):
                rule_id = flag.get("rule_id", "N/A")
                item = flag.get("item") or flag.get("description", "N/A")
                evidence = flag.get("evidence", "No evidence recorded")
                reasoning = flag.get("reasoning", "")
                is_missing_notes = flag.get("is_missing_notes", False)
                
                lines.append(f"**{i}. {rule_id}** - {item}")
                lines.append("")
                
                if is_missing_notes:
                    lines.append(f"> ⚠️ **Data Gap Identified**")
                    lines.append(f"> ")
                    lines.append(f"> {evidence[:300]}")
                else:
                    if reasoning:
                        lines.append(f"> **Reasoning:** {reasoning[:200]}")
                        lines.append(f"> ")
                    lines.append(f"> **Evidence:** {evidence[:200]}")
                
                lines.append("")
        
        # Add legend for missing notes
        missing_notes_flags = [f for f in compliance_flags if f.get("is_missing_notes", False) or 
                              check_missing_notes_context(f, extracted_data)[0]]
        if missing_notes_flags:
            lines.append("> **⚠️ Data Ingestion Notice**: Items marked with [MISSING NOTES] failed because ")
            lines.append("> the Notes to Accounts section was not included in the ingested statements. ")
            lines.append("> Only BS, PL, and CF are currently processed. To resolve these failures, ")
            lines.append("> ensure Notes to Accounts are included in the source PDF extraction.")
            lines.append("")
    else:
        lines.append("✅ No compliance flags raised.")
        lines.append("")
    
    # Risk Alerts
    risk_alerts = validation_results.get("risk_alerts", [])
    lines.append("---")
    lines.append("")
    lines.append("## Risk Analysis (Auditor Agent)")
    lines.append("")
    
    if risk_alerts:
        lines.append(f"| Risk Type | Severity | Details |")
        lines.append(f"|-----------|----------|---------|")
        for alert in risk_alerts:
            risk_type = alert.get("risk_type", "Unknown")
            severity = alert.get("severity", "N/A")
            details = alert.get("details") or alert.get("analysis") or alert.get("message") or ""
            lines.append(f"| {risk_type} | {severity} | {details[:50]} |")
        lines.append("")
    else:
        lines.append("✅ No significant risks identified.")
        lines.append("")
    
    # Footer
    lines.append("---")
    lines.append("")
    lines.append("## Disclaimer")
    lines.append("")
    lines.append("This report is generated automatically by the NFRA Compliance Engine. ")
    lines.append("It should be reviewed by qualified professionals before making any decisions.")
    lines.append("")
    lines.append(f"*Report generated on {datetime.now().strftime('%Y-%m-%d at %H:%M:%S')}*")
    
    return "\n".join(lines)


def save_report_to_disk(
    markdown_content: str,
    cin: Optional[str],
    company_name: Optional[str]
) -> str:
    """
    Save the Markdown report to the REPORT directory.
    
    Returns the file path.
    """
    # Create REPORT directory if it doesn't exist
    REPORT_DIR.mkdir(exist_ok=True)
    
    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Clean CIN/company name for filename
    if cin:
        identifier = cin.replace("/", "_").replace("\\", "_")
    elif company_name:
        identifier = company_name.replace(" ", "_").replace("/", "_")[:30]
    else:
        identifier = "UNKNOWN"
    
    filename = f"Compliance_Report_{identifier}_{timestamp}.md"
    filepath = REPORT_DIR / filename
    
    # Write file
    filepath.write_text(markdown_content, encoding="utf-8")
    
    return str(filepath)


# =============================================================================
# Main Publisher Node
# =============================================================================

def publisher_node(state: AgentState) -> AgentState:
    """
    Publisher Agent: Assembles and saves the final compliance report.
    
    - Calculates overall score from validation results
    - Generates professional Markdown report
    - Saves to REPORT/ directory
    - Updates state with final_report and final_report_path
    """
    print("--- PUBLISHER NODE ---")
    logger.info("Publisher: Generating final report")
    
    metadata = state.get("metadata", {})
    extracted_data = state.get("extracted_data", {})
    validation_results = state.get("validation_results", {})
    
    # Calculate scores
    score_info = calculate_overall_score(validation_results)
    summary = generate_summary(validation_results, extracted_data)  # Pass extracted_data for notes context
    
    # Generate report ID
    report_id = f"NFRA-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # Build final report dict
    final_report = {
        "report_id": report_id,
        "generated_at": datetime.now().isoformat(),
        "metadata": {
            "company_name": metadata.get("company_name"),
            "cin": metadata.get("cin"),
            "financial_year": metadata.get("fy"),
            "report_type": metadata.get("report_type")
        },
        "assessment": {
            "overall_score": score_info["score"],
            "grade": score_info["grade"],
            "status": score_info["status"]
        },
        "summary": {
            "critical_issues": summary["critical_issues_count"],
            "warnings": summary["warnings_count"],
            "details": summary["critical_issues"] + summary["warnings"]
        },
        "validation_details": {
            "mathematical_checks": {
                "total": len(validation_results.get("quant_errors", [])) + 4,
                "passed": 4 - len([e for e in validation_results.get("quant_errors", []) if e.get("passed") == False]),
                "failed": len([e for e in validation_results.get("quant_errors", []) if e.get("passed") == False]),
                "errors": validation_results.get("quant_errors", [])
            },
            "compliance_checks": {
                "total": 10,
                "flags": len(validation_results.get("compliance_flags", [])),
                "details": validation_results.get("compliance_flags", [])
            },
            "risk_analysis": {
                "total_alerts": len(validation_results.get("risk_alerts", [])),
                "critical": len([a for a in validation_results.get("risk_alerts", []) if str(a.get("severity", "")).upper() == "CRITICAL"]),
                "high": len([a for a in validation_results.get("risk_alerts", []) if str(a.get("severity", "")).upper() == "HIGH"]),
                "medium": len([a for a in validation_results.get("risk_alerts", []) if str(a.get("severity", "")).upper() == "MEDIUM"]),
                "alerts": validation_results.get("risk_alerts", [])
            }
        },
        "extracted_data": {
            "balance_sheet_available": extracted_data.get("balance_sheet") is not None,
            "profit_loss_available": extracted_data.get("profit_loss") is not None,
            "cash_flow_available": extracted_data.get("cash_flow") is not None
        }
    }
    
    # Format as Markdown
    markdown_report = format_report_markdown(
        metadata=metadata,
        extracted_data=extracted_data,
        validation_results=validation_results,
        score_info=score_info,
        summary=summary,
        report_id=report_id
    )
    
    # Save to disk
    try:
        report_path = save_report_to_disk(
            markdown_content=markdown_report,
            cin=metadata.get("cin"),
            company_name=metadata.get("company_name")
        )
        logger.info("Publisher: Report saved to %s", report_path)
        state["final_report_path"] = report_path
    except Exception as e:
        logger.error("Publisher: Failed to save report to disk: %s", str(e))
        state["final_report_path"] = None
    
    # Update state
    state["final_report"] = final_report
    state["processing_status"] = "completed"
    
    logger.info("Publisher: Report generated - Score: %d, Grade: %s, Status: %s",
                score_info["score"], score_info["grade"], score_info["status"])
    
    return state
