"""
Quant Agent - Pure Python mathematical validation for financial statements.

NO LLM calls - all checks are deterministic math operations.
Validates the specific JSON schema from balance_sheet.json.
"""

import logging
from typing import Dict, List, Optional, Any

from src.core.state import AgentState

logger = logging.getLogger(__name__)

# Tolerance for floating point comparisons (in lakhs)
TOLERANCE = 1.0

# Threshold for significant variance warning (50%)
VARIANCE_THRESHOLD = 0.50


# =============================================================================
# Helper Functions
# =============================================================================

def safe_get_value(data: Optional[Dict], *keys, default: float = 0.0) -> float:
    """
    Safely navigate nested dict and return float value.
    
    Example: safe_get_value(totals, "total_assets", "current_year")
    """
    if data is None:
        return default
    current = data
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
        else:
            return default
        if current is None:
            return default
    try:
        return float(current) if current is not None else default
    except (ValueError, TypeError):
        return default


# =============================================================================
# Check A: Accounting Equation (Assets = Equity + Liabilities)
# =============================================================================

def check_accounting_equation(bs_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate: total_assets == total_equity_and_liabilities
    
    Uses: bs_data['totals']['total_assets']['current_year']
          bs_data['totals']['total_equity_and_liabilities']['current_year']
    """
    totals = bs_data.get("totals", {})
    
    assets = safe_get_value(totals, "total_assets", "current_year")
    equity_liab = safe_get_value(totals, "total_equity_and_liabilities", "current_year")
    
    diff = assets - equity_liab
    passed = abs(diff) < TOLERANCE
    
    return {
        "check_name": "accounting_equation",
        "passed": passed,
        "expected": assets,
        "actual": equity_liab,
        "difference": round(diff, 2),
        "message": (
            f"PASS: Assets ({assets:,.2f}) = Equity+Liab ({equity_liab:,.2f})"
            if passed else
            f"FAIL: Assets ({assets:,.2f}) != Equity+Liab ({equity_liab:,.2f}), diff={diff:,.2f}"
        )
    }


# =============================================================================
# Check B: Vertical Consistency (Sum of Rows vs Reported Totals)
# =============================================================================

def check_vertical_consistency_assets(bs_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate: sum of all asset rows == total_assets from totals.
    
    Sums rows where section == 'assets' and is_subtotal == false.
    """
    rows = bs_data.get("rows", [])
    totals = bs_data.get("totals", {})
    
    # Sum current_year values for all asset rows (excluding subtotals)
    computed_sum = 0.0
    for row in rows:
        if row.get("section") == "assets" and not row.get("is_subtotal", False):
            value = safe_get_value(row, "values", "current_year")
            computed_sum += value
    
    reported = safe_get_value(totals, "total_assets", "current_year")
    diff = computed_sum - reported
    passed = abs(diff) < TOLERANCE
    
    return {
        "check_name": "vertical_consistency_assets",
        "passed": passed,
        "computed": round(computed_sum, 2),
        "reported": round(reported, 2),
        "difference": round(diff, 2),
        "message": (
            f"PASS: Sum of asset rows ({computed_sum:,.2f}) = Reported total ({reported:,.2f})"
            if passed else
            f"FAIL: Sum of asset rows ({computed_sum:,.2f}) != Reported total ({reported:,.2f}), diff={diff:,.2f}"
        )
    }


def check_vertical_consistency_liabilities(bs_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate: sum of all liability rows == total_liabilities from totals.
    """
    rows = bs_data.get("rows", [])
    totals = bs_data.get("totals", {})
    
    computed_sum = 0.0
    for row in rows:
        if row.get("section") == "liabilities" and not row.get("is_subtotal", False):
            value = safe_get_value(row, "values", "current_year")
            computed_sum += value
    
    reported = safe_get_value(totals, "total_liabilities", "current_year")
    diff = computed_sum - reported
    passed = abs(diff) < TOLERANCE
    
    return {
        "check_name": "vertical_consistency_liabilities",
        "passed": passed,
        "computed": round(computed_sum, 2),
        "reported": round(reported, 2),
        "difference": round(diff, 2),
        "message": (
            f"PASS: Sum of liability rows ({computed_sum:,.2f}) = Reported total ({reported:,.2f})"
            if passed else
            f"FAIL: Sum of liability rows ({computed_sum:,.2f}) != Reported total ({reported:,.2f}), diff={diff:,.2f}"
        )
    }


def check_vertical_consistency_equity(bs_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate: sum of all equity rows == total_equity from totals.
    """
    rows = bs_data.get("rows", [])
    totals = bs_data.get("totals", {})
    
    computed_sum = 0.0
    for row in rows:
        if row.get("section") == "equity" and not row.get("is_subtotal", False):
            value = safe_get_value(row, "values", "current_year")
            computed_sum += value
    
    reported = safe_get_value(totals, "total_equity", "current_year")
    diff = computed_sum - reported
    passed = abs(diff) < TOLERANCE
    
    return {
        "check_name": "vertical_consistency_equity",
        "passed": passed,
        "computed": round(computed_sum, 2),
        "reported": round(reported, 2),
        "difference": round(diff, 2),
        "message": (
            f"PASS: Sum of equity rows ({computed_sum:,.2f}) = Reported total ({reported:,.2f})"
            if passed else
            f"FAIL: Sum of equity rows ({computed_sum:,.2f}) != Reported total ({reported:,.2f}), diff={diff:,.2f}"
        )
    }


# =============================================================================
# Check C: Horizontal Consistency (Year-over-Year Variance)
# =============================================================================

def check_horizontal_consistency(bs_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Check for significant variances (>50%) between current and previous year.
    
    Returns warnings (not errors) for large movements.
    """
    rows = bs_data.get("rows", [])
    warnings: List[Dict[str, Any]] = []
    
    for row in rows:
        if row.get("is_subtotal", False):
            continue
        
        current = safe_get_value(row, "values", "current_year")
        previous = safe_get_value(row, "values", "previous_year")
        
        # Skip if previous year is zero or very small (avoid division issues)
        if abs(previous) < 0.01:
            continue
        
        variance = current - previous
        variance_pct = abs(variance) / abs(previous)
        
        if variance_pct > VARIANCE_THRESHOLD:
            warnings.append({
                "check_name": "horizontal_variance",
                "line_item": row.get("raw_label", "Unknown"),
                "normalized_label": row.get("normalized_label", ""),
                "section": row.get("section", ""),
                "current_year": round(current, 2),
                "previous_year": round(previous, 2),
                "variance": round(variance, 2),
                "variance_pct": round(variance_pct * 100, 1),
                "severity": "warning",
                "message": (
                    f"Significant variance in '{row.get('raw_label')}': "
                    f"{previous:,.2f} → {current:,.2f} ({variance_pct*100:.1f}% change)"
                )
            })
    
    return warnings


# =============================================================================
# Cross-Statement Checks
# =============================================================================

def check_cash_balance_consistency(
    bs_data: Optional[Dict[str, Any]], 
    cf_data: Optional[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """
    Validate: BS cash == CF closing cash balance.
    """
    if not bs_data or not cf_data:
        return None
    
    # Find cash from BS rows
    bs_cash = 0.0
    for row in bs_data.get("rows", []):
        normalized = row.get("normalized_label", "")
        if normalized == "cash_and_cash_equivalents":
            bs_cash = safe_get_value(row, "values", "current_year")
            break
    
    # Get closing cash from CF totals
    cf_totals = cf_data.get("totals", {})
    cf_closing = safe_get_value(cf_totals, "closing_cash_balance", "current_year")
    
    if bs_cash == 0 and cf_closing == 0:
        return None
    
    diff = bs_cash - cf_closing
    passed = abs(diff) < TOLERANCE
    
    return {
        "check_name": "cash_balance_consistency",
        "passed": passed,
        "bs_cash": round(bs_cash, 2),
        "cf_closing_cash": round(cf_closing, 2),
        "difference": round(diff, 2),
        "message": (
            f"PASS: BS Cash ({bs_cash:,.2f}) = CF Closing ({cf_closing:,.2f})"
            if passed else
            f"FAIL: BS Cash ({bs_cash:,.2f}) != CF Closing ({cf_closing:,.2f}), diff={diff:,.2f}"
        )
    }


def check_pat_calculation(pl_data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Validate: PAT = PBT - Tax Expense
    """
    if not pl_data:
        return None
    
    totals = pl_data.get("totals", {})
    pbt = safe_get_value(totals, "profit_before_tax", "current_year")
    tax = safe_get_value(totals, "tax_expense", "current_year")
    pat = safe_get_value(totals, "profit_after_tax", "current_year")
    
    if pbt == 0 and tax == 0 and pat == 0:
        return None
    
    calculated_pat = pbt - tax
    diff = pat - calculated_pat
    passed = abs(diff) < TOLERANCE
    
    return {
        "check_name": "pat_calculation",
        "passed": passed,
        "pbt": round(pbt, 2),
        "tax_expense": round(tax, 2),
        "calculated_pat": round(calculated_pat, 2),
        "reported_pat": round(pat, 2),
        "difference": round(diff, 2),
        "message": (
            f"PASS: PBT ({pbt:,.2f}) - Tax ({tax:,.2f}) = PAT ({pat:,.2f})"
            if passed else
            f"FAIL: PBT ({pbt:,.2f}) - Tax ({tax:,.2f}) = {calculated_pat:,.2f} != Reported PAT ({pat:,.2f})"
        )
    }


# =============================================================================
# Main Quant Node
# =============================================================================

def quant_node(state: AgentState) -> AgentState:
    """
    Quant Agent: Pure Python mathematical validation.
    
    Performs:
    - Check A: Accounting Equation (Assets = Equity + Liabilities)
    - Check B: Vertical Consistency (Row sums vs Totals)
    - Check C: Horizontal Consistency (YoY variance warnings)
    - Cross-statement checks (Cash, PAT)
    """
    print("--- QUANT NODE ---")
    logger.info("Quant: Starting mathematical validation")
    
    extracted = state.get("extracted_data", {})
    bs_data = extracted.get("balance_sheet")
    pl_data = extracted.get("profit_loss")
    cf_data = extracted.get("cash_flow")
    
    errors: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []
    
    # ------------------------------------
    # Balance Sheet Checks
    # ------------------------------------
    if not bs_data:
        logger.error("Quant: No balance_sheet data found in extracted_data")
        errors.append({
            "check_name": "data_availability",
            "passed": False,
            "message": "Balance sheet data is missing from extracted_data"
        })
    else:
        # Check A: Accounting Equation
        eq_result = check_accounting_equation(bs_data)
        if not eq_result["passed"]:
            errors.append(eq_result)
            logger.warning("Quant: %s", eq_result["message"])
        else:
            logger.info("Quant: %s", eq_result["message"])
        
        # Check B: Vertical Consistency
        for check_fn in [
            check_vertical_consistency_assets,
            check_vertical_consistency_liabilities,
            check_vertical_consistency_equity
        ]:
            result = check_fn(bs_data)
            if not result["passed"]:
                errors.append(result)
                logger.warning("Quant: %s", result["message"])
            else:
                logger.info("Quant: %s", result["message"])
        
        # Check C: Horizontal Consistency (warnings only)
        variance_warnings = check_horizontal_consistency(bs_data)
        warnings.extend(variance_warnings)
        for w in variance_warnings:
            logger.info("Quant: %s", w["message"])
    
    # ------------------------------------
    # Cross-Statement Checks
    # ------------------------------------
    
    # Cash balance consistency (BS vs CF)
    cash_result = check_cash_balance_consistency(bs_data, cf_data)
    if cash_result:
        if not cash_result["passed"]:
            errors.append(cash_result)
            logger.warning("Quant: %s", cash_result["message"])
        else:
            logger.info("Quant: %s", cash_result["message"])
    
    # PAT calculation (PL)
    pat_result = check_pat_calculation(pl_data)
    if pat_result:
        if not pat_result["passed"]:
            errors.append(pat_result)
            logger.warning("Quant: %s", pat_result["message"])
        else:
            logger.info("Quant: %s", pat_result["message"])
    
    # ------------------------------------
    # Update State
    # ------------------------------------
    if "validation_results" not in state or state["validation_results"] is None:
        state["validation_results"] = {
            "quant_errors": [],
            "compliance_flags": [],
            "risk_alerts": []
        }
    
    # Store errors
    state["validation_results"]["quant_errors"] = errors
    
    # Store variance warnings in risk_alerts (they're not errors, just flags)
    existing_alerts = state["validation_results"].get("risk_alerts", [])
    existing_alerts.extend([
        {
            "risk_type": "variance_warning",
            "indicator": w["normalized_label"],
            "value": w["variance_pct"],
            "threshold": VARIANCE_THRESHOLD * 100,
            "severity": "low",
            "analysis": w["message"]
        }
        for w in warnings
    ])
    state["validation_results"]["risk_alerts"] = existing_alerts
    
    state["processing_status"] = "quant_validated"
    
    logger.info(
        "Quant: Validation complete - %d errors, %d variance warnings",
        len(errors),
        len(warnings)
    )
    
    return state
