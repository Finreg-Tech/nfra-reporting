"""
Shared state definitions for NFRA multi-agent workflow.

AgentState is the central TypedDict passed through all nodes in the LangGraph.
Supports access patterns like: state['extracted_data']['balance_sheet']['totals']['total_assets']
"""

from typing import TypedDict, List, Dict, Optional, Any


# =============================================================================
# Report-Level Metadata (Gatekeeper extracts this)
# =============================================================================

class MetadataState(TypedDict):
    """High-level report metadata extracted by the Gatekeeper agent."""
    cin: Optional[str]                # Corporate Identification Number
    company_name: Optional[str]       # Legal entity name
    fy: Optional[str]                 # Financial year (e.g., "2024-25")
    report_type: Optional[str]        # "standalone" | "consolidated"
    period_end_date: Optional[str]    # e.g., "2025-03-31"


# =============================================================================
# Financial Statement Structures (matches JSON schema)
# =============================================================================

class StatementMetadata(TypedDict, total=False):
    """Metadata block within each financial statement."""
    statement_title: str
    period: str
    current_year_date: str
    previous_year_date: str
    currency: str
    unit: str


class RowValues(TypedDict, total=False):
    """Year-over-year values for a single line item."""
    current_year: Optional[float]
    previous_year: Optional[float]


class StatementRow(TypedDict, total=False):
    """A single row/line item in a financial statement."""
    section: str                      # "assets" | "liabilities" | "equity" | "income" | "expense"
    classification: Optional[str]     # "current" | "non_current" | None
    raw_label: str                    # Original label from PDF
    normalized_label: str             # Snake_case normalized key
    note_reference: Optional[str]     # Note number (e.g., "3a")
    is_subtotal: bool
    parent_label: Optional[str]       # For hierarchical grouping
    values: RowValues


class BalanceSheetTotals(TypedDict, total=False):
    """Totals block for Balance Sheet."""
    total_non_current_assets: RowValues
    total_current_assets: RowValues
    total_assets: RowValues
    total_equity: RowValues
    total_non_current_liabilities: RowValues
    total_current_liabilities: RowValues
    total_liabilities: RowValues
    total_equity_and_liabilities: RowValues


class ProfitLossTotals(TypedDict, total=False):
    """Totals block for Profit & Loss Statement."""
    total_revenue: RowValues
    total_expenses: RowValues
    profit_before_tax: RowValues
    tax_expense: RowValues
    profit_after_tax: RowValues
    other_comprehensive_income: RowValues
    total_comprehensive_income: RowValues


class CashFlowTotals(TypedDict, total=False):
    """Totals block for Cash Flow Statement."""
    net_cash_from_operating: RowValues
    net_cash_from_investing: RowValues
    net_cash_from_financing: RowValues
    net_change_in_cash: RowValues
    opening_cash: RowValues
    closing_cash: RowValues


class FinancialStatement(TypedDict, total=False):
    """Generic financial statement structure."""
    statement_type: str               # "balance_sheet" | "profit_loss" | "cash_flow"
    category: str                     # "standalone" | "consolidated"
    metadata: StatementMetadata
    rows: List[StatementRow]
    totals: Dict[str, RowValues]      # Flexible totals dict


# =============================================================================
# Validation Results (Quant, Accountant, Auditor populate these)
# =============================================================================

class QuantError(TypedDict, total=False):
    """A quantitative validation error from Quant agent."""
    check_name: str                   # e.g., "accounting_equation"
    passed: bool
    expected: Optional[float]
    actual: Optional[float]
    difference: Optional[float]
    message: str


class ComplianceFlag(TypedDict, total=False):
    """A compliance/regulatory flag from Accountant agent."""
    rule_id: str                      # e.g., "NFRA-001"
    description: str
    severity: str                     # "critical" | "warning" | "info"
    evidence: Optional[str]
    recommendation: Optional[str]


class RiskAlert(TypedDict, total=False):
    """A risk alert from Auditor agent."""
    risk_type: str                    # e.g., "liquidity_risk", "solvency_risk"
    indicator: str                    # e.g., "current_ratio"
    value: Optional[float]
    threshold: Optional[float]
    severity: str                     # "high" | "medium" | "low"
    analysis: Optional[str]


class ValidationResultsState(TypedDict):
    """Aggregated validation results from all validation agents."""
    quant_errors: List[QuantError]
    compliance_flags: List[ComplianceFlag]
    risk_alerts: List[RiskAlert]


# =============================================================================
# Main Agent State (passed through LangGraph workflow)
# =============================================================================

class AgentState(TypedDict):
    """
    Central state object for the NFRA multi-agent workflow.
    
    Access patterns:
        state['metadata']['company_name']
        state['extracted_data']['balance_sheet']['totals']['total_assets']['current_year']
        state['validation_results']['quant_errors'][0]['message']
        state['markdown_content']['full_text']  # For searching Notes to Accounts
    """
    # Input
    file_path: str                              # Path to uploaded PDF
    
    # Gatekeeper outputs
    metadata: MetadataState                     # Report-level metadata (CIN, company, FY)
    
    # Extracted financial data (Dict[str, Any] for flexibility)
    # Keys: "balance_sheet", "profit_loss", "cash_flow"
    # Each value follows FinancialStatement structure
    extracted_data: Dict[str, Any]
    
    # Raw markdown content from PDF (for Accountant/Auditor note lookups)
    # Keys: "balance_sheet", "profit_loss", "cash_flow", "notes", "full_text"
    # "full_text" is concatenated BS + PL + CF + Notes for downstream searching
    markdown_content: Dict[str, str]
    
    # Validation outputs
    validation_results: ValidationResultsState
    
    # RAG context (retrieved chunks for compliance checking)
    rag_context: List[Dict[str, Any]]
    
    # Publisher output
    final_report: Dict[str, Any]
    final_report_path: Optional[str]            # Path to saved Markdown report (REPORT/*.md)
    
    # Workflow status
    processing_status: str                      # "pending" | "processing" | "completed" | "failed"
