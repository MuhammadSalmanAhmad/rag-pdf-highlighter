import logging
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import FileResponse
from langchain_core.documents import Document
from pydantic import BaseModel, Field

from rag_pdf_highlighter.exceptions import HighlightError, PDFDownloadError
from rag_pdf_highlighter.utils.pdf_helpers import cleanup_file, download_pdf, highlight_chunks_in_pdf

# ── Configure logging ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
logger = logging.getLogger("highlight-service")

app = FastAPI(
    title="Callisto PDF Highlighter",
    description="Highlight text chunks in PDFs for RAG pipelines",
    version="0.1.0",
)


class DocumentPayload(BaseModel):
    page_content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class HighlightRequest(BaseModel):
    pdf_url: str
    documents: list[DocumentPayload]


@app.get("/")
async def health_check() -> dict[str, str]:
    return {"status": "ok the app is running"}


@app.post("/highlight")
async def highlight(payload: HighlightRequest, background_tasks: BackgroundTasks) -> FileResponse:
    logger.info("Received /highlight request – %d chunks", len(payload.documents))

    pdf_path: str | None = None
    output_path: str | None = None

    try:
        pdf_path = await download_pdf(payload.pdf_url)

        documents = [
            Document(page_content=item.page_content, metadata=item.metadata)
            for item in payload.documents
        ]

        output_path = highlight_chunks_in_pdf(pdf_path=pdf_path, documents=documents)

        background_tasks.add_task(cleanup_file, pdf_path)
        background_tasks.add_task(cleanup_file, output_path)

        return FileResponse(
            path=output_path,
            media_type="application/pdf",
            filename="highlighted.pdf",
        )
    except PDFDownloadError as exc:
        if pdf_path:
            cleanup_file(pdf_path)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HighlightError as exc:
        if pdf_path:
            cleanup_file(pdf_path)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        if pdf_path:
            cleanup_file(pdf_path)
        raise
    except Exception as exc:
        logger.exception("Highlighting failed")
        if pdf_path:
            cleanup_file(pdf_path)
        raise HTTPException(status_code=500, detail=f"Highlighting failed: {exc}") from exc
