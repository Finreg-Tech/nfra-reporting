import logging
import json
from typing import Dict, List, Optional, Any
from src.core.state import AgentState
from resources.prompts.prompts import AUDITOR_RISK_PROMPT
from langchain_openai import ChatOpenAI
from config import OPENAI_API_KEY, OPENAI_MODEL

logger = logging.getLogger(__name__)

llm = ChatOpenAI(
    model=OPENAI_MODEL,
    temperature=0,
    api_key=OPENAI_API_KEY
)

RISK_THRESHOLDS = {
    "debt_equity_ratio": 2.0,
    "current_ratio_min": 1.0,
    "interest_coverage_min": 1.5,
    "negative_working_capital": True,
    "declining_revenue": True
}

def safe_get(data: Optional[Dict], *keys, default=0.0) -> float:
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

def analyze_liquidity_risk(bs_data: Optional[Dict]) -> List[Dict]:
    alerts = []
    if not bs_data:
        return alerts
    
    totals = bs_data.get("totals", {})
    current_assets = safe_get(totals, "current_assets")
    current_liabilities = safe_get(totals, "current_liabilities")
    
    if current_liabilities > 0:
        current_ratio = current_assets / current_liabilities
        if current_ratio < RISK_THRESHOLDS["current_ratio_min"]:
            alerts.append({
                "risk_type": "Liquidity Risk",
                "severity": "HIGH",
                "metric": "Current Ratio",
                "value": round(current_ratio, 2),
                "threshold": RISK_THRESHOLDS["current_ratio_min"],
                "details": f"Current ratio ({current_ratio:.2f}) below minimum threshold",
                "source": "quantitative"
            })
    
    working_capital = current_assets - current_liabilities
    if working_capital < 0:
        alerts.append({
            "risk_type": "Working Capital Risk",
            "severity": "HIGH",
            "metric": "Working Capital",
            "value": working_capital,
            "threshold": 0,
            "details": f"Negative working capital: {working_capital}",
            "source": "quantitative"
        })
    
    return alerts

def analyze_solvency_risk(bs_data: Optional[Dict]) -> List[Dict]:
    alerts = []
    if not bs_data:
        return alerts
    
    totals = bs_data.get("totals", {})
    total_debt = safe_get(totals, "total_liabilities")
    total_equity = safe_get(totals, "total_equity")
    
    if total_equity > 0:
        debt_equity = total_debt / total_equity
        if debt_equity > RISK_THRESHOLDS["debt_equity_ratio"]:
            alerts.append({
                "risk_type": "Solvency Risk",
                "severity": "MEDIUM",
                "metric": "Debt-Equity Ratio",
                "value": round(debt_equity, 2),
                "threshold": RISK_THRESHOLDS["debt_equity_ratio"],
                "details": f"Debt-equity ratio ({debt_equity:.2f}) exceeds threshold",
                "source": "quantitative"
            })
    elif total_equity <= 0 and total_debt > 0:
        alerts.append({
            "risk_type": "Solvency Risk",
            "severity": "CRITICAL",
            "metric": "Equity",
            "value": total_equity,
            "threshold": 0,
            "details": "Negative or zero equity with existing debt",
            "source": "quantitative"
        })
    
    return alerts

def analyze_profitability_risk(pl_data: Optional[Dict]) -> List[Dict]:
    alerts = []
    if not pl_data:
        return alerts
    
    totals = pl_data.get("totals", {})
    pat = safe_get(totals, "profit_after_tax")
    total_revenue = safe_get(totals, "total_revenue")
    
    if pat < 0:
        alerts.append({
            "risk_type": "Profitability Risk",
            "severity": "HIGH",
            "metric": "Net Loss",
            "value": pat,
            "threshold": 0,
            "details": f"Company reported net loss: {pat}",
            "source": "quantitative"
        })
    
    if total_revenue > 0 and pat > 0:
        net_margin = (pat / total_revenue) * 100
        if net_margin < 1:
            alerts.append({
                "risk_type": "Profitability Risk",
                "severity": "MEDIUM",
                "metric": "Net Profit Margin",
                "value": round(net_margin, 2),
                "threshold": 1,
                "details": f"Very low net margin: {net_margin:.2f}%",
                "source": "quantitative"
            })
    
    return alerts

def analyze_cash_flow_risk(cf_data: Optional[Dict]) -> List[Dict]:
    alerts = []
    if not cf_data:
        return alerts
    
    totals = cf_data.get("totals", {})
    operating_cf = safe_get(totals, "operating_activities")
    if operating_cf == 0:
        operating_cf = safe_get(totals, "net_cash_from_operating")
    
    if operating_cf < 0:
        alerts.append({
            "risk_type": "Cash Flow Risk",
            "severity": "HIGH",
            "metric": "Operating Cash Flow",
            "value": operating_cf,
            "threshold": 0,
            "details": "Negative cash flow from operations",
            "source": "quantitative"
        })
    
    return alerts

def llm_qualitative_risk_analysis(extracted_data: Dict, rag_context: List[Dict]) -> Dict[str, Any]:
    financial_summary = {
        "balance_sheet_available": extracted_data.get("balance_sheet") is not None,
        "profit_loss_available": extracted_data.get("profit_loss") is not None,
        "cash_flow_available": extracted_data.get("cash_flow") is not None
    }
    
    if extracted_data.get("balance_sheet"):
        bs = extracted_data["balance_sheet"]
        financial_summary["balance_sheet_totals"] = bs.get("totals", {})
    
    if extracted_data.get("profit_loss"):
        pl = extracted_data["profit_loss"]
        financial_summary["profit_loss_totals"] = pl.get("totals", {})
    
    auditor_notes = ""
    for ctx in rag_context[:3]:
        if ctx.get("section_name") and "audit" in ctx.get("section_name", "").lower():
            auditor_notes += ctx.get("actual_text", "") + "\n"
    
    chain = AUDITOR_RISK_PROMPT | llm
    
    try:
        response = chain.invoke({
            "financial_data": json.dumps(financial_summary, indent=2),
            "auditor_notes": auditor_notes if auditor_notes else "No auditor notes available"
        })
        
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        
        return json.loads(content)
        
    except json.JSONDecodeError:
        return {
            "risk_level": "Unknown",
            "flags": [],
            "overall_assessment": response.content,
            "recommendations": [],
            "source": "llm_qualitative"
        }
    except Exception as e:
        logger.error("LLM risk analysis failed: %s", str(e))
        return {
            "risk_level": "Unknown",
            "flags": [],
            "overall_assessment": f"Analysis failed: {str(e)}",
            "recommendations": [],
            "source": "llm_qualitative"
        }

def auditor_node(state: AgentState) -> AgentState:
    print("--- AUDITOR NODE ---")
    logger.info("Auditor: Starting hybrid risk analysis (Quantitative + AI)")
    
    extracted = state.get("extracted_data", {})
    rag_context = state.get("rag_context", [])
    
    # Get full markdown text for risk analysis (populated by Gatekeeper)
    full_text = state.get("markdown_content", {}).get("full_text", "")
    if full_text:
        logger.info("Auditor: Received %d chars of markdown for analysis", len(full_text))
    
    bs_data = extracted.get("balance_sheet")
    pl_data = extracted.get("profit_loss")
    cf_data = extracted.get("cash_flow")
    
    risk_alerts: List[Dict] = []
    
    logger.info("Auditor: Phase 1 - Quantitative analysis (Python)")
    risk_alerts.extend(analyze_liquidity_risk(bs_data))
    risk_alerts.extend(analyze_solvency_risk(bs_data))
    risk_alerts.extend(analyze_profitability_risk(pl_data))
    risk_alerts.extend(analyze_cash_flow_risk(cf_data))
    
    for alert in risk_alerts:
        logger.warning("Auditor [Quant]: %s - %s (%s)", alert["risk_type"], alert["details"], alert["severity"])
    
    logger.info("Auditor: Phase 2 - Qualitative analysis (LLM)")
    llm_analysis = llm_qualitative_risk_analysis(extracted, rag_context)
    
    for flag in llm_analysis.get("flags", []):
        risk_alerts.append({
            "risk_type": flag.get("category", "Qualitative Risk"),
            "severity": flag.get("severity", "MEDIUM"),
            "metric": "LLM Analysis",
            "value": None,
            "threshold": None,
            "details": flag.get("description", ""),
            "evidence": flag.get("evidence"),
            "source": "llm_qualitative"
        })
        logger.warning("Auditor [LLM]: %s - %s", flag.get("category"), flag.get("description"))
    
    if "validation_results" not in state or state["validation_results"] is None:
        state["validation_results"] = {"quant_errors": [], "compliance_flags": [], "risk_alerts": []}
    
    state["validation_results"]["risk_alerts"] = risk_alerts
    state["validation_results"]["llm_risk_summary"] = {
        "overall_risk_level": llm_analysis.get("risk_level"),
        "assessment": llm_analysis.get("overall_assessment"),
        "recommendations": llm_analysis.get("recommendations", [])
    }
    state["processing_status"] = "risk_analyzed"
    
    logger.info("Auditor: Risk analysis complete - %d alerts (Quant + LLM)", len(risk_alerts))
    return state
