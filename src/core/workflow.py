import logging
from typing import Dict
from langgraph.graph import StateGraph, START, END
from src.core.state import AgentState
from src.core.agents.gatekeeper import gatekeeper_node
from src.core.agents.quant import quant_node
from src.core.agents.accountant import accountant_node
from src.core.agents.auditor import auditor_node
from src.core.agents.publisher import publisher_node

logger = logging.getLogger(__name__)

def create_workflow() -> StateGraph:
    workflow = StateGraph(AgentState)
    
    workflow.add_node("gatekeeper", gatekeeper_node)
    workflow.add_node("quant", quant_node)
    workflow.add_node("accountant", accountant_node)
    workflow.add_node("auditor", auditor_node)
    workflow.add_node("publisher", publisher_node)
    
    workflow.add_edge(START, "gatekeeper")
    workflow.add_edge("gatekeeper", "quant")
    workflow.add_edge("quant", "accountant")
    workflow.add_edge("accountant", "auditor")
    workflow.add_edge("auditor", "publisher")
    workflow.add_edge("publisher", END)
    
    return workflow

app = create_workflow().compile()

async def run_validation_chain(file_path: str) -> Dict:
    logger.info("Starting validation chain for: %s", file_path)
    
    initial_state: AgentState = {
        "file_path": file_path,
        "metadata": {
            "cin": None,
            "fy": None,
            "company_name": None,
            "report_type": None
        },
        "extracted_data": {
            "balance_sheet": None,
            "profit_loss": None,
            "cash_flow": None
        },
        "validation_results": {
            "quant_errors": [],
            "compliance_flags": [],
            "risk_alerts": []
        },
        "rag_context": [],
        "final_report": {},
        "processing_status": "initialized",
        "markdown_content": {}
    }
    
    try:
        final_state = await app.ainvoke(initial_state)
        logger.info("Validation chain completed successfully")
        return final_state
    except Exception as e:
        logger.error("Validation chain failed: %s", str(e))
        raise
