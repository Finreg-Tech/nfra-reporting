# NFRA Reporting

# NFRA - Financial Statement Compliance Validation System

**Date:** February 14, 2026

---

## What This System Does

A **multi-agent AI system** that validates financial statements against **Ind AS (Indian Accounting Standards)** compliance requirements using LangGraph, RAG, and LLM-powered analysis.

**Input:** Annual Report PDF  
**Output:** Comprehensive compliance validation report (Markdown + JSON)

### Key Capabilities

| Feature | Description |
|---------|-------------|
| **PDF Extraction** | ML-powered page classification + LlamaParse table extraction |
| **Mathematical Validation** | Automated balance checks, ratio analysis |
| **Ind AS Compliance** | Knowledge Graph + RAG-based standard verification |
| **Risk Assessment** | Financial health indicators and red flags |
| **Professional Reports** | Detailed Markdown reports with grades and recommendations |

---

## Quick Start

### Installation

```bash
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file:

```env
OPENAI_API_KEY=your_openai_key
LLAMA_CLOUD_API_KEY=your_llamaparse_key
API_HOST=0.0.0.0
API_PORT=8000
```

### Start the API Server

```bash
uvicorn src.api.server:app --host 0.0.0.0 --port 8000
```

### Validate a Financial Report

```bash
curl -X POST "http://localhost:8000/validate_report" \
  -F "file=@annual_report.pdf"
```

---

## System Architecture

### Multi-Agent Workflow (LangGraph)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     NFRA COMPLIANCE VALIDATION PIPELINE                      │
└─────────────────────────────────────────────────────────────────────────────┘

    ┌──────────────┐
    │  PDF Upload  │
    └──────┬───────┘
           │
           ▼
╔══════════════════════════════════════════════════════════════════════════════╗
║  GATEKEEPER AGENT                                                            ║
║  ├─ ML page classification (BS, PL, Cash Flow, Notes)                        ║
║  ├─ LlamaParse table extraction                                              ║
║  ├─ LLM-powered JSON structuring                                             ║
║  └─ Schema validation                                                        ║
╚══════════════════════════════════╤═══════════════════════════════════════════╝
                                   │
                                   ▼
╔══════════════════════════════════════════════════════════════════════════════╗
║  QUANT AGENT (No LLM - Pure Python)                                          ║
║  ├─ Balance Sheet equation: Assets = Equity + Liabilities                    ║
║  ├─ Cash Flow reconciliation                                                 ║
║  ├─ Year-over-year variance analysis                                         ║
║  └─ Financial ratio calculations                                             ║
╚══════════════════════════════════╤═══════════════════════════════════════════╝
                                   │
                                   ▼
╔══════════════════════════════════════════════════════════════════════════════╗
║  ACCOUNTANT AGENT                                                            ║
║  ├─ Knowledge Graph lookup (line item → Ind AS standard)                     ║
║  ├─ RAG retrieval of relevant accounting rules                               ║
║  └─ LLM compliance verification with reasoning                               ║
╚══════════════════════════════════╤═══════════════════════════════════════════╝
                                   │
                                   ▼
╔══════════════════════════════════════════════════════════════════════════════╗
║  AUDITOR AGENT                                                               ║
║  ├─ Risk indicator analysis                                                  ║
║  ├─ Going concern assessment                                                 ║
║  └─ LLM-powered audit observations                                           ║
╚══════════════════════════════════╤═══════════════════════════════════════════╝
                                   │
                                   ▼
╔══════════════════════════════════════════════════════════════════════════════╗
║  PUBLISHER AGENT (No LLM - Pure Python)                                      ║
║  ├─ Aggregate all validation results                                         ║
║  ├─ Calculate compliance score and grade                                     ║
║  ├─ Generate professional Markdown report                                    ║
║  └─ Save to REPORT/ directory                                                ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/validate_report` | POST | Full compliance validation pipeline |
| `/NFRA` | POST | Extract structured JSON from PDF |
| `/ingest` | POST | Ingest regulatory documents into RAG |
| `/NFRA-QUERY` | POST | Query Ind AS rules by standard code |
| `/rag-query` | POST | Semantic search over regulations |
| `/health` | GET | Health check |

---

## Project Structure

```
Fin-LLM-NFRA/
├── config/
│   ├── __init__.py           # Re-exports all settings
│   ├── settings.py           # Configuration constants
│   └── logging.py            # Logging configuration
├── src/
│   ├── api/
│   │   ├── server.py         # FastAPI application
│   │   └── routes/
│   │       ├── ingest.py     # Document ingestion
│   │       ├── nfra_query.py # Structured queries
│   │       └── rag_query.py  # Semantic search
│   ├── core/
│   │   ├── state.py          # LangGraph state definition
│   │   ├── workflow.py       # Agent orchestration
│   │   └── agents/
│   │       ├── gatekeeper.py # PDF extraction & validation
│   │       ├── quant.py      # Mathematical checks
│   │       ├── accountant.py # Ind AS compliance
│   │       ├── auditor.py    # Risk assessment
│   │       └── publisher.py  # Report generation
│   ├── services/
│   │   ├── database/         # PostgreSQL + pgvector
│   │   ├── rag/              # RAG retrieval services
│   │   └── extraction/llm/   # LLM-based extraction
│   └── utils/
│       └── preprocessing.py  # Text utilities
├── resources/
│   ├── models/               # ML pickle files
│   └── prompts/
│       ├── prompts.py        # LangChain prompt templates
│       ├── knowledge_graph.json  # Line item → Ind AS mapping
│       └── *.j2              # Jinja2 extraction templates
├── REPORT/                   # Generated compliance reports
├── tests/
├── requirements.txt
└── README.md
```

---

## ML Page Classification

The system uses ML to identify financial statement pages before processing:

| Category | Keywords Detected |
|----------|-------------------|
| **Balance Sheet** | assets, liabilities, equity, property |
| **Profit & Loss** | revenue, expenses, profit, cost of goods |
| **Cash Flow** | cash flows, operating activities, financing |
| **Notes** | accounting policies, disclosure, valuation |

**Optimization:** ML classifies pages locally (free, fast), then only relevant pages are sent to LlamaParse API - **90%+ reduction in API costs**.

---

## Technology Stack

| Component | Purpose |
|-----------|---------|
| **LangGraph** | Multi-agent workflow orchestration |
| **FastAPI** | Async REST API server |
| **LangChain + OpenAI** | LLM-powered compliance analysis |
| **PostgreSQL + pgvector** | Vector database for RAG |
| **PyMuPDF (fitz)** | PDF text extraction (local, fast) |
| **LlamaParse** | High-quality table extraction (API) |
| **Logistic Regression + Random Forest** | ML page classification |
| **TF-IDF Vectorizer** | Text feature extraction |

---

## Compliance Grading

| Grade | Score Range | Description |
|-------|-------------|-------------|
| A | 90-100 | Excellent compliance |
| B | 80-89 | Good compliance with minor issues |
| C | 70-79 | Acceptable with improvement needed |
| D | 60-69 | Below standard, significant issues |
| F | 0-59 | Non-compliant, major concerns |

---

## Sample Output

### Compliance Report

```markdown
# NFRA Compliance Validation Report

**Company:** Example Corp Ltd
**Financial Year:** 2024-25
**Generated:** 2026-02-14

## Executive Summary

| Metric | Value |
|--------|-------|
| **Overall Score** | 85/100 |
| **Grade** | B |
| **Critical Issues** | 2 |
| **Warnings** | 3 |

## ✅ Successful Validations

- Property, Plant & Equipment: Compliant with Ind AS 16
- Revenue Recognition: Compliant with Ind AS 115
- Financial Instruments: Compliant with Ind AS 109

## ❌ Critical Issues

- Deferred Tax: FAIL for Ind AS 12
  - *Reason:* Note reference exists but note text unavailable for verification
```

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key for LLM | Required |
| `LLAMA_CLOUD_API_KEY` | LlamaParse API key | Required |
| `API_HOST` | Server host | `0.0.0.0` |
| `API_PORT` | Server port | `8000` |
| `DATABASE_URL` | PostgreSQL connection | Required for RAG |
| `LOG_LEVEL` | Logging level | `INFO` |

---

## License

MIT License
