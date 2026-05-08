import logging
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import FileResponse
from langchain_core.documents import Document
from pydantic import BaseModel, Field
from src.utils.pdf_helpers import cleanup_file, download_pdf, highlight_chunks_in_pdf

# ── Configure logging ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
logger = logging.getLogger("highlight-service")

app = FastAPI()


class DocumentPayload(BaseModel):
    page_content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class HighlightRequest(BaseModel):
    pdf_url: str
    documents: list[DocumentPayload]


@app.get("/")
async def health_check():
    return {"status": "ok the app is running"}


@app.post("/highlight")
async def highlight(payload: HighlightRequest, background_tasks: BackgroundTasks):
    logger.info("Received /highlight request – %d chunks", len(payload.documents))

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
    except HTTPException:
        if "pdf_path" in locals():
            cleanup_file(pdf_path)
        raise
    except Exception as exc:
        logger.exception("Highlighting failed")
        if "pdf_path" in locals():
            cleanup_file(pdf_path)
        raise HTTPException(status_code=500, detail=f"Highlighting failed: {exc}") from exc
