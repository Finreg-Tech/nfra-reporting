"""
Database Handshake Verification Test.

Confirms that the Accountant Agent can find Ind AS rules in the database.
Tests the RAG retrieval service against known Knowledge Graph keys.

Usage:
    python -m tests.test_db_handshake

Author: QA Engineering
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from RAG.retrieval_service import retrieve_rules


# =============================================================================
# Test Configuration (matches Accountant Agent hardcoded values)
# =============================================================================

TEST_CASES = [
    {"document_type": "IndAS", "standard_code": "Ind AS 16", "description": "Property, Plant & Equipment"},
    {"document_type": "IndAS", "standard_code": "Ind AS 116", "description": "Leases"},
    {"document_type": "IndAS", "standard_code": "Ind AS 109", "description": "Financial Instruments"},
    {"document_type": "IndAS", "standard_code": "Ind AS 37", "description": "Provisions"},
]


# =============================================================================
# Test Functions
# =============================================================================

def test_retrieve_rules(document_type: str, standard_code: str, description: str) -> bool:
    """
    Test retrieval of rules for a specific standard.
    
    Returns True if rules found, False otherwise.
    """
    print(f"\n{'='*60}")
    print(f"  Testing: {standard_code} ({description})")
    print(f"  Document Type: {document_type}")
    print(f"{'='*60}")
    
    try:
        rules = retrieve_rules(
            document_type=document_type,
            standard_code=standard_code
        )
        
        rule_count = len(rules) if rules else 0
        print(f"  📊 Chunks found: {rule_count}")
        
        if rule_count > 0:
            # Print preview of first chunk
            first_rule = rules[0]
            
            # Try to get content from various possible keys
            content = (
                first_rule.get("actual_text") or 
                first_rule.get("content") or 
                first_rule.get("text") or
                str(first_rule)
            )
            
            preview = content[:100] if content else "(empty)"
            print(f"  📄 First chunk preview:")
            print(f"     \"{preview}...\"")
            
            # Show metadata if available
            if isinstance(first_rule, dict):
                section = first_rule.get("section_name", "N/A")
                page = first_rule.get("page_number", "N/A")
                print(f"  📍 Section: {section}, Page: {page}")
            
            print(f"  ✅ SUCCESS - Rules found in database")
            return True
        else:
            print(f"  ❌ FAILED - No rules found!")
            print()
            print("  " + "=" * 56)
            print("  ⚠️  DATABASE MISMATCH WARNING ⚠️")
            print("  " + "=" * 56)
            print(f"  The Accountant Agent expects document_type='IndAS'")
            print(f"  but no rules were found for standard_code='{standard_code}'")
            print()
            print("  Possible fixes:")
            print("  1. Re-ingest Ind AS PDFs with document_type='IndAS'")
            print("  2. Check if the database has been populated")
            print("  3. Verify standard_code format matches (e.g., 'Ind AS 16')")
            print("  " + "=" * 56)
            return False
            
    except Exception as e:
        print(f"  💥 ERROR: {type(e).__name__}: {str(e)[:100]}")
        return False


def run_all_tests() -> None:
    """Run all database handshake tests."""
    print("\n" + "=" * 60)
    print("  NFRA Database Handshake Verification")
    print("  Checking Accountant Agent → RAG Database Connection")
    print("=" * 60)
    
    results = []
    
    for test_case in TEST_CASES:
        passed = test_retrieve_rules(
            document_type=test_case["document_type"],
            standard_code=test_case["standard_code"],
            description=test_case["description"]
        )
        results.append({
            "standard": test_case["standard_code"],
            "passed": passed
        })
    
    # Summary
    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    
    passed_count = sum(1 for r in results if r["passed"])
    total_count = len(results)
    
    for result in results:
        emoji = "✅" if result["passed"] else "❌"
        status = "PASS" if result["passed"] else "FAIL"
        print(f"  {emoji} {result['standard']}: {status}")
    
    print()
    print(f"  Total: {passed_count}/{total_count} passed")
    
    if passed_count == total_count:
        print("\n  🎉 All tests passed! Database handshake successful.")
    elif passed_count == 0:
        print("\n  ❌ ALL TESTS FAILED!")
        print("  ❌ The database appears to have NO Ind AS rules ingested.")
        print("  ❌ Run the ingestion pipeline first with document_type='IndAS'")
    else:
        print(f"\n  ⚠️  {total_count - passed_count} test(s) failed.")
        print("  Some standards may not have been ingested.")
    
    # Exit with appropriate code
    sys.exit(0 if passed_count == total_count else 1)


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    run_all_tests()
