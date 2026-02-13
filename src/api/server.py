import logging
import os
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse

from config import API_HOST, API_PORT, MAX_FILE_SIZE_BYTES
from src.services.database.db_init import init_db
from src.api.routes.ingest import router as ingest_router
from src.api.routes.nfra_query import router as nfra_query_router
from src.api.routes.rag_query import router as rag_query_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup")
    logger.info("Initializing database...")
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error("Database initialization failed: %s", e)
    yield
    logger.info("Application shutdown")


app = FastAPI(
    title="Financial Statement Processor",
    description="API for processing financial statement PDFs into structured JSON",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(ingest_router)
app.include_router(nfra_query_router)
app.include_router(rag_query_router)


def validate_pdf_file(filename: str | None, content_type: str | None, content_length: int) -> None:
    if not filename:
        raise HTTPException(status_code=400, detail="No file provided")

    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    if content_type and content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Invalid content type")

    if content_length == 0:
        raise HTTPException(status_code=400, detail="Empty file uploaded")

    if content_length > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="File too large")


def sanitize_filename(filename: str) -> str:
    stem = Path(filename).stem
    return "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in stem)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "healthy"}


@app.post("/validate_report")
async def validate_report(file: UploadFile = File(...)) -> dict[str, Any]:
    from src.core.workflow import run_validation_chain
    import time
    
    logger.info("=== VALIDATE_REPORT REQUEST ===")
    logger.info("Received file: %s (content_type: %s)", file.filename, file.content_type)
    
    try:
        content = await file.read()
        logger.info("File read successfully: %d bytes", len(content))
    except IOError as e:
        logger.error("Error reading uploaded file: %s", e)
        raise HTTPException(status_code=400, detail="Error reading uploaded file")

    validate_pdf_file(file.filename, file.content_type, len(content))
    logger.info("PDF validation passed")

    temp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(content)
            temp_path = tmp.name
        logger.info("Temp file created: %s", temp_path)

        logger.info("Starting validation chain for: %s", file.filename)
        start_time = time.time()
        
        result = await run_validation_chain(temp_path)
        
        elapsed = time.time() - start_time
        logger.info("Validation chain completed in %.2f seconds", elapsed)
        
        # Log result summary
        final_report = result.get("final_report", {})
        status = result.get("processing_status", "unknown")
        report_path = result.get("final_report_path", "N/A")
        score = final_report.get("assessment", {}).get("overall_score", "N/A")
        grade = final_report.get("assessment", {}).get("grade", "N/A")
        
        logger.info("Processing status: %s", status)
        logger.info("Report saved to: %s", report_path)
        logger.info("Compliance score: %s/100 (Grade: %s)", score, grade)
        logger.info("=== VALIDATE_REPORT COMPLETE ===")
        
        return final_report

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Validation error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")

    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
                logger.debug("Temp file cleaned up: %s", temp_path)
            except OSError as e:
                logger.warning("Failed to delete temporary file: %s", e)


@app.post("/NFRA")
async def process_financials(file: UploadFile = File(...)) -> dict[str, Any]:
    from src.services.extraction.llm.extractor import extract_financial_markdown
    from src.services.extraction.llm.pipeline import process_company
    
    try:
        content = await file.read()
    except IOError as e:
        logger.error("Error reading uploaded file: %s", e)
        raise HTTPException(status_code=400, detail="Error reading uploaded file")

    validate_pdf_file(file.filename, file.content_type, len(content))

    temp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(content)
            temp_path = tmp.name

        company_name = sanitize_filename(file.filename or "unknown")
        logger.info("Processing file: %s", file.filename)

        data = extract_financial_markdown(temp_path, company_name=company_name)

        if not data:
            raise HTTPException(status_code=400, detail="Failed to extract financial data from PDF")

        result = await process_company(
            data["company_name"],
            data.get("balance_sheet_md"),
            data.get("profit_loss_md"),
            data.get("cash_flow_md")
        )

        logger.info("Successfully processed: %s", data["company_name"])

        return {
            "company_name": data["company_name"],
            "balance_sheet": result.get("balance_sheet"),
            "profit_and_loss": result.get("profit_and_loss"),
            "cash_flow": result.get("cash_flow")
        }

    except HTTPException:
        raise
    except ValueError as e:
        logger.error("Validation error: %s", e)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Processing error: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error during processing")

    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except OSError as e:
                logger.warning("Failed to delete temporary file: %s", e)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=API_HOST, port=API_PORT)
