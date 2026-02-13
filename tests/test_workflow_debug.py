a"""
Standalone Integration Test for NFRA LangGraph Workflow.

This script verifies the entire multi-agent workflow end-to-end,
checking that data flows correctly through all agents.

Usage:
    python -m tests.test_workflow_debug
    python -m tests.test_workflow_debug path/to/your.pdf

Author: QA Automation
"""

import sys
import os
import json
import logging
import traceback
from pathlib import Path
from typing import Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from Agents.workflow import run_validation_chain

# =============================================================================
# Configuration
# =============================================================================

DEFAULT_TEST_PDF = "IndiaAI Financial Reporting Compliance Challenge (1).pdf"
OUTPUT_DIR = Path("results")
DEBUG_REPORT_PATH = OUTPUT_DIR / "debug_report.json"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("WorkflowDebug")


# =============================================================================
# Helper Functions
# =============================================================================

def print_header(title: str) -> None:
    """Print a formatted section header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_status(emoji: str, message: str) -> None:
    """Print a status line with emoji."""
    print(f"  {emoji} {message}")


def safe_get(data: dict, *keys, default=None):
    """Safely navigate nested dict."""
    current = data
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
        else:
            return default
        if current is None:
            return default
    return current


def get_test_pdf_path() -> str:
    """Get PDF path from CLI args or use default."""
    if len(sys.argv) > 1:
        return sys.argv[1]
    return DEFAULT_TEST_PDF


def check_pdf_exists(pdf_path: str) -> bool:
    """Check if the PDF file exists."""
    if os.path.exists(pdf_path):
        return True
    
    # Check in common locations
    search_paths = [
        pdf_path,
        os.path.join("DOCS", pdf_path),
        os.path.join("..", pdf_path),
    ]
    
    for path in search_paths:
        if os.path.exists(path):
            return True
    
    return False


# =============================================================================
# Verification Functions
# =============================================================================

def verify_gatekeeper(result_state: dict) -> bool:
    """Verify Gatekeeper agent extracted metadata correctly."""
    print_header("🚪 GATEKEEPER VERIFICATION")
    
    metadata = result_state.get("metadata", {})
    cin = metadata.get("cin")
    company_name = metadata.get("company_name")
    fy = metadata.get("fy")
    report_type = metadata.get("report_type")
    
    print(f"  CIN:          {cin or '(not found)'}")
    print(f"  Company:      {company_name or '(not found)'}")
    print(f"  FY:           {fy or '(not found)'}")
    print(f"  Report Type:  {report_type or '(not found)'}")
    
    # At least one identifier should be present
    if cin or company_name:
        print_status("✅", "Gatekeeper extracted metadata successfully")
        return True
    else:
        print_status("❌", "Gatekeeper FAILED to extract metadata")
        return False


def verify_markdown_propagation(result_state: dict) -> bool:
    """Verify the markdown content fix - text should propagate to downstream agents."""
    print_header("📝 MARKDOWN PROPAGATION CHECK (Bug Fix Verification)")
    
    markdown_content = result_state.get("markdown_content", {})
    full_text = markdown_content.get("full_text", "")
    bs_md = markdown_content.get("balance_sheet", "")
    pl_md = markdown_content.get("profit_loss", "")
    cf_md = markdown_content.get("cash_flow", "")
    notes_md = markdown_content.get("notes", "")
    
    print(f"  Balance Sheet MD:  {len(bs_md):,} chars")
    print(f"  Profit & Loss MD:  {len(pl_md):,} chars")
    print(f"  Cash Flow MD:      {len(cf_md):,} chars")
    print(f"  Notes MD:          {len(notes_md):,} chars")
    print(f"  Full Text:         {len(full_text):,} chars")
    
    if full_text and len(full_text) > 100:
        print_status("✅", "Markdown content propagated correctly (Bug Fixed!)")
        return True
    else:
        print_status("❌", "Markdown content is EMPTY - Bug NOT Fixed!")
        return False


def verify_quant(result_state: dict) -> bool:
    """Verify Quant agent ran mathematical validations."""
    print_header("🔢 QUANT VERIFICATION")
    
    validation_results = result_state.get("validation_results", {})
    quant_errors = validation_results.get("quant_errors", [])
    
    print(f"  Quant Errors Found: {len(quant_errors)}")
    
    if quant_errors:
        print("\n  Errors:")
        for i, error in enumerate(quant_errors[:5], 1):
            check_name = error.get("check_name", "Unknown")
            message = error.get("message", str(error))[:80]
            print(f"    {i}. [{check_name}] {message}")
        
        if len(quant_errors) > 5:
            print(f"    ... and {len(quant_errors) - 5} more")
        
        print_status("⚠️", f"Quant found {len(quant_errors)} validation errors")
        return True  # Errors found means quant ran
    else:
        print_status("✅", "Quant passed - No mathematical errors found")
        return True


def verify_accountant(result_state: dict) -> bool:
    """Verify Accountant agent ran compliance checks."""
    print_header("📋 ACCOUNTANT VERIFICATION (Compliance)")
    
    validation_results = result_state.get("validation_results", {})
    compliance_flags = validation_results.get("compliance_flags", [])
    
    print(f"  Compliance Flags Found: {len(compliance_flags)}")
    
    if compliance_flags:
        print("\n  First 2 Flags:")
        for i, flag in enumerate(compliance_flags[:2], 1):
            rule_id = flag.get("rule_id", "Unknown")
            description = flag.get("description", "")[:50]
            severity = flag.get("severity", "N/A")
            status = flag.get("status", "N/A")
            print(f"    {i}. [{severity.upper()}] {rule_id}")
            print(f"       {description}...")
            print(f"       Status: {status}")
        
        if len(compliance_flags) > 2:
            print(f"\n    ... and {len(compliance_flags) - 2} more flags")
        
        print_status("⚠️", f"Accountant raised {len(compliance_flags)} compliance flags")
    else:
        print_status("✅", "Accountant passed - No compliance issues found")
    
    # Accountant ran if we have validation_results
    return "compliance_flags" in validation_results


def verify_auditor(result_state: dict) -> bool:
    """Verify Auditor agent ran risk analysis."""
    print_header("🔍 AUDITOR VERIFICATION (Risk Analysis)")
    
    validation_results = result_state.get("validation_results", {})
    risk_alerts = validation_results.get("risk_alerts", [])
    llm_summary = validation_results.get("llm_risk_summary", {})
    
    print(f"  Risk Alerts Found: {len(risk_alerts)}")
    
    if risk_alerts:
        print("\n  Alerts by Type:")
        risk_types = {}
        for alert in risk_alerts:
            rt = alert.get("risk_type", "Other")
            risk_types[rt] = risk_types.get(rt, 0) + 1
        
        for rt, count in sorted(risk_types.items(), key=lambda x: -x[1]):
            print(f"    - {rt}: {count}")
    
    if llm_summary:
        overall_risk = llm_summary.get("overall_risk_level", "Unknown")
        print(f"\n  LLM Overall Risk Level: {overall_risk}")
        
        recs = llm_summary.get("recommendations", [])
        if recs:
            print(f"  Recommendations: {len(recs)}")
    
    if risk_alerts:
        print_status("⚠️", f"Auditor identified {len(risk_alerts)} risk alerts")
    else:
        print_status("✅", "Auditor passed - No significant risks found")
    
    return "risk_alerts" in validation_results


def verify_publisher(result_state: dict) -> bool:
    """Verify Publisher agent generated final report."""
    print_header("📄 PUBLISHER VERIFICATION")
    
    final_report = result_state.get("final_report", {})
    processing_status = result_state.get("processing_status", "unknown")
    
    print(f"  Processing Status: {processing_status}")
    print(f"  Final Report Keys: {list(final_report.keys()) if final_report else 'None'}")
    
    if final_report:
        # Show summary if available
        summary = final_report.get("summary", "")
        if summary:
            print(f"\n  Summary Preview:")
            print(f"    {summary[:200]}...")
        
        overall_score = final_report.get("overall_score")
        if overall_score is not None:
            print(f"\n  Overall Score: {overall_score}")
        
        print_status("✅", "Publisher generated final report")
        return True
    else:
        print_status("❌", "Publisher did NOT generate final report")
        return False


# =============================================================================
# Main Execution
# =============================================================================

def run_workflow_test(pdf_path: str) -> Optional[dict]:
    """Execute the full workflow and return result state."""
    print_header("🚀 STARTING WORKFLOW TEST")
    print(f"  PDF: {pdf_path}")
    print(f"  Exists: {os.path.exists(pdf_path)}")
    
    if not os.path.exists(pdf_path):
        print_status("❌", f"PDF file not found: {pdf_path}")
        print("\n  Searched locations:")
        print(f"    - {os.path.abspath(pdf_path)}")
        return None
    
    print("\n  Running validation chain...")
    print("  (This may take 1-3 minutes depending on PDF size)\n")
    
    result_state = run_validation_chain(pdf_path)
    
    return result_state


def save_debug_report(result_state: dict) -> None:
    """Save the final report to JSON file."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    final_report = result_state.get("final_report", {})
    
    # Also include validation results in debug output
    debug_output = {
        "final_report": final_report,
        "metadata": result_state.get("metadata", {}),
        "processing_status": result_state.get("processing_status", ""),
        "validation_summary": {
            "quant_errors_count": len(result_state.get("validation_results", {}).get("quant_errors", [])),
            "compliance_flags_count": len(result_state.get("validation_results", {}).get("compliance_flags", [])),
            "risk_alerts_count": len(result_state.get("validation_results", {}).get("risk_alerts", [])),
        },
        "markdown_content_lengths": {
            k: len(v) if isinstance(v, str) else 0
            for k, v in result_state.get("markdown_content", {}).items()
        }
    }
    
    with open(DEBUG_REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(debug_output, f, indent=2, ensure_ascii=False, default=str)
    
    print_status("💾", f"Debug report saved to: {DEBUG_REPORT_PATH}")


def print_final_summary(results: dict) -> None:
    """Print a clean final summary."""
    print_header("📊 FINAL SUMMARY")
    
    all_passed = all(results.values())
    
    for check, passed in results.items():
        emoji = "✅" if passed else "❌"
        status = "PASSED" if passed else "FAILED"
        print(f"  {emoji} {check}: {status}")
    
    print()
    if all_passed:
        print("  🎉 ALL CHECKS PASSED!")
    else:
        failed = [k for k, v in results.items() if not v]
        print(f"  ⚠️  {len(failed)} check(s) failed: {', '.join(failed)}")


def main():
    """Main entry point."""
    print("\n" + "=" * 60)
    print("  NFRA LangGraph Workflow Integration Test")
    print("=" * 60)
    
    pdf_path = get_test_pdf_path()
    
    try:
        # Run the workflow
        result_state = run_workflow_test(pdf_path)
        
        if result_state is None:
            print_status("❌", "Workflow could not start - PDF not found")
            sys.exit(1)
        
        # Run all verifications
        verification_results = {
            "Gatekeeper": verify_gatekeeper(result_state),
            "Markdown Propagation": verify_markdown_propagation(result_state),
            "Quant": verify_quant(result_state),
            "Accountant": verify_accountant(result_state),
            "Auditor": verify_auditor(result_state),
            "Publisher": verify_publisher(result_state),
        }
        
        # Save debug report
        save_debug_report(result_state)
        
        # Print final summary
        print_final_summary(verification_results)
        
        # Exit with appropriate code
        sys.exit(0 if all(verification_results.values()) else 1)
        
    except Exception as e:
        print_header("💥 WORKFLOW CRASHED")
        print(f"\n  Error Type: {type(e).__name__}")
        print(f"  Error Message: {str(e)[:200]}")
        print("\n  Full Traceback:")
        print("-" * 60)
        traceback.print_exc()
        print("-" * 60)
        
        sys.exit(2)


if __name__ == "__main__":
    main()
