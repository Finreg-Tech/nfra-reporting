"""
Full System Integration Test for NFRA LangGraph Pipeline.

This test validates the entire workflow from PDF input to report generation.

Usage:
    python -m tests.test_full_system
    python -m tests.test_full_system path/to/your.pdf
"""

import asyncio
import os
import sys
import traceback
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# =============================================================================
# Test Configuration
# =============================================================================

# Default test PDF paths (checked in order)
DEFAULT_PDF_CANDIDATES = [
    "IndiaAI Financial Reporting Compliance Challenge (1).pdf",
    "test_data/sample_report.pdf",
    "DOCS/sample.pdf",
]


def find_test_pdf(custom_path: str = None) -> str | None:
    """
    Find a valid PDF file for testing.
    
    Args:
        custom_path: Optional custom path provided via command line
        
    Returns:
        Absolute path to PDF if found, None otherwise
    """
    if custom_path:
        path = Path(custom_path)
        if path.exists() and path.suffix.lower() == ".pdf":
            return str(path.resolve())
        print(f"⚠️  Provided path not found or not a PDF: {custom_path}")
        return None
    
    # Search default candidates
    for candidate in DEFAULT_PDF_CANDIDATES:
        path = PROJECT_ROOT / candidate
        if path.exists():
            return str(path.resolve())
    
    return None


# =============================================================================
# Main Test Function
# =============================================================================

async def run_full_system_test(pdf_path: str) -> bool:
    """
    Execute the full system integration test.
    
    Args:
        pdf_path: Path to the PDF file to process
        
    Returns:
        True if all assertions pass, False otherwise
    """
    from Agents.workflow import run_validation_chain
    
    print("=" * 60)
    print("NFRA Full System Integration Test")
    print("=" * 60)
    print(f"\n📄 Input PDF: {pdf_path}")
    print(f"📁 File Size: {os.path.getsize(pdf_path):,} bytes")
    print("\n" + "-" * 60)
    print("Starting LangGraph Pipeline...")
    print("-" * 60 + "\n")
    
    # Execute the validation chain
    final_state = await run_validation_chain(pdf_path)
    
    print("\n" + "-" * 60)
    print("Pipeline Execution Complete. Running Assertions...")
    print("-" * 60 + "\n")
    
    # ==========================================================================
    # ASSERTION 1: Processing Status
    # ==========================================================================
    print("🔍 Assertion 1: Processing Status")
    processing_status = final_state.get("processing_status")
    print(f"   Expected: 'completed'")
    print(f"   Actual:   '{processing_status}'")
    
    assert processing_status == "completed", (
        f"Processing status mismatch: expected 'completed', got '{processing_status}'"
    )
    print("   ✅ PASSED\n")
    
    # ==========================================================================
    # ASSERTION 2: Final Report Not Empty
    # ==========================================================================
    print("🔍 Assertion 2: Final Report Generation")
    final_report = final_state.get("final_report", {})
    print(f"   Expected: Non-empty dict")
    print(f"   Actual:   Dict with {len(final_report)} keys")
    
    assert final_report, "Final report is empty or missing"
    assert isinstance(final_report, dict), f"Final report is not a dict: {type(final_report)}"
    assert len(final_report) > 0, "Final report has no keys"
    print("   ✅ PASSED\n")
    
    # ==========================================================================
    # ASSERTION 3: Report File Exists on Disk
    # ==========================================================================
    print("🔍 Assertion 3: Report File Saved to Disk")
    report_path = final_state.get("final_report_path")
    print(f"   Expected: Valid file path that exists")
    print(f"   Actual:   '{report_path}'")
    
    assert report_path is not None, "final_report_path is None"
    assert os.path.exists(report_path), f"Report file does not exist: {report_path}"
    print("   ✅ File exists\n")
    
    # ==========================================================================
    # ASSERTION 4: Report File Size > 0
    # ==========================================================================
    print("🔍 Assertion 4: Report File Size")
    file_size = os.path.getsize(report_path)
    print(f"   Expected: > 0 bytes")
    print(f"   Actual:   {file_size:,} bytes")
    
    assert file_size > 0, f"Report file is empty (0 bytes): {report_path}"
    print("   ✅ PASSED\n")
    
    # ==========================================================================
    # Additional Validation Checks
    # ==========================================================================
    print("🔍 Bonus Checks: Report Content Validation")
    
    # Check report structure
    assert "report_id" in final_report, "Missing 'report_id' in final report"
    assert "assessment" in final_report, "Missing 'assessment' in final report"
    
    assessment = final_report.get("assessment", {})
    score = assessment.get("overall_score")
    grade = assessment.get("grade")
    status = assessment.get("status")
    
    print(f"   📊 Score: {score}/100")
    print(f"   📝 Grade: {grade}")
    print(f"   📋 Status: {status}")
    print("   ✅ Report structure valid\n")
    
    # ==========================================================================
    # Summary
    # ==========================================================================
    print("=" * 60)
    print("✅ SYSTEM VALIDATION PASSED!")
    print("=" * 60)
    print(f"\n📄 Generated Report: {report_path}")
    print(f"📊 Compliance Score: {score}/100 (Grade: {grade})")
    
    # Show critical issues if any
    summary = final_report.get("summary", {})
    critical = summary.get("critical_issues", 0)
    warnings = summary.get("warnings", 0)
    
    if critical > 0 or warnings > 0:
        print(f"⚠️  Issues Found: {critical} critical, {warnings} warnings")
    else:
        print("✨ No compliance issues detected")
    
    print("\n" + "=" * 60)
    
    return True


# =============================================================================
# Entry Point
# =============================================================================

def main():
    """Main entry point for the test script."""
    # Get custom PDF path from command line if provided
    custom_path = sys.argv[1] if len(sys.argv) > 1 else None
    
    # Find test PDF
    pdf_path = find_test_pdf(custom_path)
    
    if pdf_path is None:
        print("=" * 60)
        print("⚠️  TEST SKIPPED: No PDF file found")
        print("=" * 60)
        print("\nTo run this test, either:")
        print("  1. Place a PDF in the project root named:")
        for candidate in DEFAULT_PDF_CANDIDATES:
            print(f"     - {candidate}")
        print("  2. Pass a PDF path as argument:")
        print("     python -m tests.test_full_system path/to/your.pdf")
        print("\n" + "=" * 60)
        sys.exit(0)  # Exit with 0 (skip, not failure)
    
    try:
        success = asyncio.run(run_full_system_test(pdf_path))
        sys.exit(0 if success else 1)
        
    except AssertionError as e:
        print("\n" + "=" * 60)
        print("❌ ASSERTION FAILED")
        print("=" * 60)
        print(f"\nError: {e}")
        print("\nFull Traceback:")
        print("-" * 60)
        traceback.print_exc()
        sys.exit(1)
        
    except Exception as e:
        print("\n" + "=" * 60)
        print("❌ TEST FAILED WITH EXCEPTION")
        print("=" * 60)
        print(f"\nError Type: {type(e).__name__}")
        print(f"Error Message: {e}")
        print("\nFull Traceback:")
        print("-" * 60)
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
