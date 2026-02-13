

---

# 🔥 FINAL IMPLEMENTATION INSTRUCTION FOR COPILOT

## NFRA Deterministic Rule Engine + Auto DB Setup

You are modifying my existing **Fin-LLM-NFRA** project.

This is a full backend refactor.

---

# 🎯 OBJECTIVE

1. Convert RAG to deterministic metadata engine.
2. Remove embeddings + similarity logic.
3. Add `/ingest` endpoint.
4. Add `/NFRA-QUERY` endpoint.
5. Move all DB-related logic inside `DB/` folder.
6. Automatically create database + tables from `.env`.
7. No vector operations.
8. Clean modular architecture.

---

# 🧱 PROJECT STRUCTURE (MANDATORY)

Refactor project to:

```
    api/
        main.py
        ingest.py
        nfra_query.py

    rag/
        pdf_parser.py
        section_splitter.py
        ingestion_service.py
        retrieval_service.py

    DB/
        db_config.py
        db_init.py
        models.py

.env
```

DO NOT mix DB logic inside rag folder.

All database logic must stay inside `DB/`.

---

# 🗄️ DATABASE CONFIGURATION

## 📌 1️⃣ Use .env

Add:

```
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=postgres
DB_NAME=nfra_db
```

Use `python-dotenv` to load environment variables.

---

## 📌 2️⃣ Database Auto Creation Logic

In `DB/db_init.py`:

When application starts:

1. Connect to default postgres database.
2. Check if `DB_NAME` exists.
3. If not → create it.
4. Then connect to created DB.
5. Create tables automatically if not exist.

Use:

```python
CREATE DATABASE nfra_db;
```

Then create table:

```sql
CREATE TABLE IF NOT EXISTS rules (
    id SERIAL PRIMARY KEY,
    document_type TEXT NOT NULL,
    standard_code TEXT NOT NULL,
    standard_number INTEGER,
    standard_name TEXT,
    section_name TEXT,
    section_order INTEGER,
    chunk TEXT,
    actual_text TEXT
);
```

This must run automatically when app starts.

---

# 🧠 REMOVE VECTOR LOGIC

Completely delete:

* embedding generation
* pgvector usage
* similarity search
* RRF ranking
* vector columns
* vector indexes

There must be ZERO vector operations in this system.

---

# 📌 INGEST ENDPOINT

## Route:

```
POST /ingest
```

## Input:

* file: PDF (multipart/form-data)
* rules: IndAS | SEBI | RBI | CompanyAct

---

## Ingestion Flow

1. Use PyMuPDF:

```python
import fitz
doc = fitz.open(file)
```

2. Extract text page by page.
3. Detect standard header using:

```
Ind AS \d+,
```

4. Extract:

   * standard_code
   * standard_number
   * standard_name

5. Detect sections using title-style detection.

6. Chunk strictly:

```
Standard → Section → Full Section Text
```

One DB row per section.

NO token-based chunking.
NO similarity logic.

7. Insert using DB service inside `DB/`.

Return:

```
{
  "message": "Ingestion successful",
  "sections_inserted": count
}
```

---

# 📌 NFRA QUERY ENDPOINT

## Route:

```
POST /NFRA-QUERY
```

## Input JSON:

```
{
  "document_type": "IndAS",      // mandatory
  "standard_code": "Ind AS 21",  // mandatory
  "standard_number": 21,         // optional
  "section_name": "Functional currency", // optional
  "section_order": 2             // optional
}
```

---

## Retrieval Logic

1. Validate:

   * document_type required
   * standard_code required

2. Build dynamic SQL:

Base:

```
WHERE document_type = ?
AND standard_code = ?
```

Add optional filters if provided.

3. Return rows with:

```
document_type
standard_code
standard_number
standard_name
section_name
section_order
chunk
actual_text
```

NO ranking.
NO similarity.
NO embeddings.

Pure deterministic filtering.

---

# 🗂 DB SERVICE DESIGN

Inside `DB/`:

### db_config.py

* Load .env
* Create engine / connection pool

### db_init.py

* Create database if not exists
* Create tables if not exist
* Run on app startup

### models.py

* Define rules table schema
* Insert function
* Query function

Routes must call DB functions from DB folder only.

---

# 🚀 APPLICATION STARTUP BEHAVIOR

When app runs:

1. Load environment variables.
2. Initialize database.
3. Create DB if not exists.
4. Create tables if not exists.
5. Then start FastAPI.

---

# 🛑 STRICT RULES

Do NOT:

* Reintroduce vector search
* Add embeddings
* Add RAG similarity
* Use old preprocessing module
* Use old chunking file
* Hardcode DB credentials
* Mix DB logic inside rag folder

---

# 🏆 FINAL SYSTEM

You are building:

NFRA Deterministic Regulatory Rule Engine

Not semantic RAG.

---

# 🔥 EXPECTED FINAL FLOW

## Ingestion

```
Upload PDF
→ Extract text
→ Detect standard
→ Detect sections
→ Store in DB
```

## Retrieval

```
POST /NFRA-QUERY
→ SQL filter
→ Return rule sections
```

---

# 🎯 SUCCESS CRITERIA

* Database auto-creates
* Tables auto-create
* No vector usage
* Clean modular structure
* Ingestion works
* Metadata filtering works
