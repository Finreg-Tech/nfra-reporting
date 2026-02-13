from typing import Literal, Optional

from pydantic import BaseModel, Field


# =============================================================================
# COMMON VALUE STRUCTURE - FIXED FIELDS FOR ALL STATEMENTS
# =============================================================================

class PeriodValues(BaseModel):
    """Fixed structure for period values - always current and previous year."""
    current_year: Optional[float] = None
    previous_year: Optional[float] = None


# =============================================================================
# BALANCE SHEET SCHEMA
# =============================================================================

class BalanceSheetRow(BaseModel):
    section: Literal["assets", "equity", "liabilities"]
    classification: Literal["current", "non_current"] | None = None
    raw_label: str
    normalized_label: str
    note_reference: Optional[str] = None
    is_subtotal: bool = False
    parent_label: Optional[str] = None
    values: PeriodValues


class BalanceSheetTotals(BaseModel):
    total_non_current_assets: Optional[PeriodValues] = None
    total_current_assets: Optional[PeriodValues] = None
    total_assets: Optional[PeriodValues] = None
    total_equity: Optional[PeriodValues] = None
    total_non_current_liabilities: Optional[PeriodValues] = None
    total_current_liabilities: Optional[PeriodValues] = None
    total_liabilities: Optional[PeriodValues] = None
    total_equity_and_liabilities: Optional[PeriodValues] = None


class BalanceSheetMetadata(BaseModel):
    statement_title: Optional[str] = None
    period: Optional[str] = None
    current_year_date: Optional[str] = Field(None, description="ISO date YYYY-MM-DD")
    previous_year_date: Optional[str] = Field(None, description="ISO date YYYY-MM-DD")
    currency: Optional[str] = None
    unit: Optional[str] = Field(None, description="e.g., 'lakhs', 'crores', 'millions'")


class BalanceSheetSchema(BaseModel):
    statement_type: Literal["balance_sheet"] = "balance_sheet"
    category: Literal["standalone", "consolidated"]
    metadata: BalanceSheetMetadata
    rows: list[BalanceSheetRow]
    totals: BalanceSheetTotals


# =============================================================================
# PROFIT AND LOSS SCHEMA
# =============================================================================

class ProfitLossRow(BaseModel):
    section: Literal["income", "expenses", "tax", "other_comprehensive_income", "eps"]
    raw_label: str
    normalized_label: str
    note_reference: Optional[str] = None
    is_subtotal: bool = False
    parent_label: Optional[str] = None
    values: PeriodValues


class ProfitLossTotals(BaseModel):
    total_income: Optional[PeriodValues] = None
    total_expenses: Optional[PeriodValues] = None
    profit_before_tax: Optional[PeriodValues] = None
    tax_expense: Optional[PeriodValues] = None
    profit_after_tax: Optional[PeriodValues] = None
    other_comprehensive_income: Optional[PeriodValues] = None
    total_comprehensive_income: Optional[PeriodValues] = None
    basic_eps: Optional[PeriodValues] = None
    diluted_eps: Optional[PeriodValues] = None


class ProfitLossMetadata(BaseModel):
    statement_title: Optional[str] = None
    period: Optional[str] = None
    current_year_date: Optional[str] = Field(None, description="ISO date YYYY-MM-DD")
    previous_year_date: Optional[str] = Field(None, description="ISO date YYYY-MM-DD")
    currency: Optional[str] = None
    unit: Optional[str] = Field(None, description="e.g., 'lakhs', 'crores', 'millions'")


class ProfitLossSchema(BaseModel):
    statement_type: Literal["profit_and_loss"] = "profit_and_loss"
    category: Literal["standalone", "consolidated"]
    metadata: ProfitLossMetadata
    rows: list[ProfitLossRow]
    totals: ProfitLossTotals


# =============================================================================
# CASH FLOW SCHEMA
# =============================================================================

class CashFlowRow(BaseModel):
    activity_type: Literal["operating", "investing", "financing"]
    raw_label: str
    normalized_label: str
    note_reference: Optional[str] = None
    is_subtotal: bool = False
    parent_label: Optional[str] = None
    values: PeriodValues


class CashFlowTotals(BaseModel):
    net_cash_from_operating: Optional[PeriodValues] = None
    net_cash_from_investing: Optional[PeriodValues] = None
    net_cash_from_financing: Optional[PeriodValues] = None
    net_increase_in_cash: Optional[PeriodValues] = None
    opening_cash_balance: Optional[PeriodValues] = None
    closing_cash_balance: Optional[PeriodValues] = None


class CashFlowMetadata(BaseModel):
    statement_title: Optional[str] = None
    period: Optional[str] = None
    current_year_date: Optional[str] = Field(None, description="ISO date YYYY-MM-DD")
    previous_year_date: Optional[str] = Field(None, description="ISO date YYYY-MM-DD")
    currency: Optional[str] = None
    unit: Optional[str] = Field(None, description="e.g., 'lakhs', 'crores', 'millions'")


class CashFlowSchema(BaseModel):
    statement_type: Literal["cash_flow"] = "cash_flow"
    category: Literal["standalone", "consolidated"]
    metadata: CashFlowMetadata
    rows: list[CashFlowRow]
    totals: CashFlowTotals
