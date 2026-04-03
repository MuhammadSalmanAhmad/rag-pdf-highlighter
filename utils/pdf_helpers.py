import os
import tempfile
from pathlib import Path

import fitz
import httpx
from fastapi import HTTPException
from langchain_core.documents import Document


def cleanup_file(path: str) -> None:
    if os.path.exists(path):
        os.unlink(path)


async def download_pdf(url: str) -> str:
    pdf_tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    pdf_tmp_path = pdf_tmp.name
    pdf_tmp.close()

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(url)
            response.raise_for_status()

        with open(pdf_tmp_path, "wb") as f:
            f.write(response.content)
    except Exception as exc:
        cleanup_file(pdf_tmp_path)
        raise HTTPException(status_code=400, detail=f"Failed to download PDF: {exc}") from exc

    return pdf_tmp_path


def highlight_chunks_in_pdf(pdf_path: str, documents: list[Document]) -> str:
    if not documents:
        raise HTTPException(status_code=400, detail="No documents provided")
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=400, detail=f"PDF not found: {pdf_path}")

    source_file = Path(pdf_path)
    output_tmp = tempfile.NamedTemporaryFile(
        suffix=f"_highlighted{source_file.suffix}",
        delete=False,
    )
    output_tmp.close()
    output_path = output_tmp.name

    doc = fitz.open(pdf_path)
    try:
        for chunk in documents:
            page_number = int(chunk.metadata.get("page", 0))
            text_to_highlight = " ".join(chunk.page_content.split())

            if not text_to_highlight:
                continue
            if page_number < 0 or page_number >= len(doc):
                continue

            page = doc[page_number]
            matches = page.search_for(text_to_highlight)
            for match in matches:
                page.add_highlight_annot(match)

        doc.save(output_path)
    finally:
        doc.close()

    return output_path
