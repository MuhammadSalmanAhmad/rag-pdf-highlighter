"""
pdf_helpers.py
~~~~~~~~~~~~~~
Utilities for downloading a PDF, searching for text chunks across pages,
and applying highlight annotations.  Three search strategies are tried in
order of specificity (exact → sentence → collapsed-whitespace).
"""

import logging
import os
import re
import tempfile
from pathlib import Path

import fitz
import httpx
from langchain_core.documents import Document

from src.exceptions import NoDocumentsError, PDFDownloadError, PDFNotFoundError

logger = logging.getLogger("highlight-service.pdf_helpers")

# Convenience alias used in return types throughout the module.
Rects = list[fitz.Rect]


# ── File I/O ───────────────────────────────────────────────────────────────


def cleanup_file(path: str) -> None:
    """Silently delete *path* if it exists."""
    if os.path.exists(path):
        os.unlink(path)


async def download_pdf(url: str) -> str:
    """Download a PDF from *url* and return the path to a temp file."""
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    tmp_path = tmp.name
    tmp.close()

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(url)
            response.raise_for_status()

        Path(tmp_path).write_bytes(response.content)
    except Exception as exc:
        logger.exception("Failed to download PDF from %s", url)
        cleanup_file(tmp_path)
        raise PDFDownloadError(f"Failed to download PDF: {exc}") from exc

    return tmp_path


# ── Text normalisation helpers ─────────────────────────────────────────────


def _normalize(text: str) -> str:
    """Collapse whitespace runs into a single space and strip edges."""
    return " ".join(text.split())


def _collapse(text: str) -> str:
    """Remove **all** whitespace (useful for char-spaced PDF artifacts)."""
    return re.sub(r"\s+", "", text)


def _split_sentences(text: str) -> list[str]:
    """Break *text* into sentence-like fragments (≥ 20 chars each)."""
    parts = re.split(r"(?<=[.!?:;])\s+|\n+", text)
    return [p.strip() for p in parts if len(p.strip()) > 20]


# ── Search strategies ──────────────────────────────────────────────────────


def _search_exact(page: fitz.Page, text: str) -> Rects:
    """Strategy 1 – search for the full normalised text verbatim."""
    return page.search_for(text)


def _search_by_sentence(page: fitz.Page, text: str) -> Rects:
    """Strategy 2 – split into sentences and search each independently."""
    rects: Rects = []
    for sentence in _split_sentences(text):
        rects.extend(page.search_for(sentence))
    return rects


def _search_collapsed(page: fitz.Page, text: str) -> Rects:
    """
    Strategy 3 – handle PDFs where characters are individually spaced
    (e.g. "W H A T" stored in the text layer instead of "WHAT").

    We strip all whitespace from both the page text and the query, slide a
    fixed-length window across the collapsed query, find matching positions
    in the collapsed page text, map those positions back to the original
    page text, then search for the recovered span.
    """
    page_text = page.get_text("text")
    page_collapsed = _collapse(page_text)
    chunk_collapsed = _collapse(text)

    if len(chunk_collapsed) < 10:
        return []

    fragment_len = min(60, len(chunk_collapsed))
    step = max(fragment_len // 2, 20)
    rects: Rects = []

    for start in range(0, len(chunk_collapsed) - fragment_len + 1, step):
        fragment = chunk_collapsed[start : start + fragment_len]
        pos = page_collapsed.find(fragment)
        while pos != -1:
            orig_start = _map_collapsed_pos(page_text, pos)
            orig_end = _map_collapsed_pos(page_text, pos + fragment_len)

            if orig_start is not None and orig_end is not None:
                span = page_text[orig_start:orig_end].strip()
                if span:
                    rects.extend(page.search_for(span))

            pos = page_collapsed.find(fragment, pos + 1)

    return _dedupe_rects(rects)


def _search_with_fallbacks(page: fitz.Page, text: str) -> Rects:
    """
    Run each search strategy in order, returning as soon as one succeeds.
    """
    for strategy in (_search_exact, _search_by_sentence, _search_collapsed):
        if rects := strategy(page, text):
            return rects
    return []


# ── Internal geometry helpers ──────────────────────────────────────────────


def _map_collapsed_pos(original_text: str, collapsed_pos: int) -> int | None:
    """
    Map a character index in the *collapsed* (whitespace-free) string back
    to the corresponding index in *original_text*.
    """
    count = 0
    for i, ch in enumerate(original_text):
        if not ch.isspace():
            if count == collapsed_pos:
                return i
            count += 1
    return len(original_text) if count == collapsed_pos else None


def _dedupe_rects(rects: Rects, threshold: float = 5.0) -> Rects:
    """Remove near-duplicate rectangles (within *threshold* points)."""
    if not rects:
        return rects

    unique: Rects = [rects[0]]
    for rect in rects[1:]:
        already_present = any(
            abs(rect.x0 - u.x0) < threshold
            and abs(rect.y0 - u.y0) < threshold
            and abs(rect.x1 - u.x1) < threshold
            and abs(rect.y1 - u.y1) < threshold
            for u in unique
        )
        if not already_present:
            unique.append(rect)
    return unique


# ── Main entry point ──────────────────────────────────────────────────────


def highlight_chunks_in_pdf(pdf_path: str, documents: list[Document]) -> str:
    """
    Open the PDF at *pdf_path*, highlight every chunk in *documents*,
    and return the path to a new temporary file with annotations applied.
    """
    if not documents:
        raise NoDocumentsError("No documents provided")
    if not os.path.exists(pdf_path):
        raise PDFNotFoundError(f"PDF not found: {pdf_path}")

    output_fd, output_path = tempfile.mkstemp(
        suffix=f"_highlighted{Path(pdf_path).suffix}",
    )
    os.close(output_fd)

    doc = fitz.open(pdf_path)
    total_highlights = 0

    try:
        for chunk in documents:
            page_number = int(chunk.metadata.get("page", 0))
            text = _normalize(chunk.page_content)

            if not text or not (0 <= page_number < len(doc)):
                continue

            page = doc[page_number]
            for rect in _search_with_fallbacks(page, text):
                page.add_highlight_annot(rect)
                total_highlights += 1

        doc.save(output_path)
        logger.info("Highlighting complete – %d highlights applied", total_highlights)
    finally:
        doc.close()

    return output_path
