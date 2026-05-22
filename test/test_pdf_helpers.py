import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.documents import Document

from rag_pdf_highlighter.exceptions import NoDocumentsError, PDFDownloadError, PDFNotFoundError
from rag_pdf_highlighter.utils.pdf_helpers import cleanup_file, download_pdf, highlight_chunks_in_pdf


# ---------------------------------------------------------------------------
# cleanup_file
# ---------------------------------------------------------------------------

def test_cleanup_file_deletes_existing_file(tmp_path):
    f = tmp_path / "test.pdf"
    f.write_bytes(b"data")
    cleanup_file(str(f))
    assert not f.exists()


def test_cleanup_file_does_not_raise_for_missing_file():
    cleanup_file("/nonexistent/path/file.pdf")  # should not raise


# ---------------------------------------------------------------------------
# download_pdf
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_download_pdf_success(tmp_path):
    pdf_bytes = b"%PDF-1.4 fake content"

    mock_response = MagicMock()
    mock_response.content = pdf_bytes
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("rag_pdf_highlighter.utils.pdf_helpers.httpx.AsyncClient", return_value=mock_client):
        path = await download_pdf("https://example.com/sample.pdf")

    assert os.path.exists(path)
    with open(path, "rb") as f:
        assert f.read() == pdf_bytes
    cleanup_file(path)


@pytest.mark.asyncio
async def test_download_pdf_raises_on_error():
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=Exception("connection refused"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("rag_pdf_highlighter.utils.pdf_helpers.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(PDFDownloadError) as exc_info:
            await download_pdf("https://example.com/bad.pdf")

    assert "Failed to download PDF" in str(exc_info.value)


@pytest.mark.asyncio
async def test_download_pdf_cleans_up_temp_file_on_error():
    created_paths = []

    original_named_temp = __import__("tempfile").NamedTemporaryFile

    def tracking_named_temp(**kwargs):
        f = original_named_temp(**kwargs)
        created_paths.append(f.name)
        return f

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=Exception("fail"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("rag_pdf_highlighter.utils.pdf_helpers.httpx.AsyncClient", return_value=mock_client):
        with patch("rag_pdf_highlighter.utils.pdf_helpers.tempfile.NamedTemporaryFile", side_effect=tracking_named_temp):
            with pytest.raises(PDFDownloadError):
                await download_pdf("https://example.com/bad.pdf")

    for path in created_paths:
        assert not os.path.exists(path), f"Temp file was not cleaned up: {path}"


# ---------------------------------------------------------------------------
# highlight_chunks_in_pdf
# ---------------------------------------------------------------------------

def test_highlight_chunks_raises_on_empty_documents(tmp_pdf):
    with pytest.raises(NoDocumentsError) as exc_info:
        highlight_chunks_in_pdf(pdf_path=tmp_pdf, documents=[])
    assert "No documents provided" in str(exc_info.value)


def test_highlight_chunks_raises_when_pdf_not_found():
    doc = Document(page_content="some text", metadata={"page": 0})
    with pytest.raises(PDFNotFoundError) as exc_info:
        highlight_chunks_in_pdf(pdf_path="/nonexistent/path.pdf", documents=[doc])
    assert "PDF not found" in str(exc_info.value)


def test_highlight_chunks_returns_valid_pdf_path(tmp_pdf):
    doc = Document(page_content="Hello world this is a test document", metadata={"page": 0})
    output = highlight_chunks_in_pdf(pdf_path=tmp_pdf, documents=[doc])
    assert os.path.exists(output)
    assert output.endswith(".pdf")
    cleanup_file(output)


def test_highlight_chunks_skips_out_of_range_page(tmp_pdf):
    doc = Document(page_content="some text", metadata={"page": 99})
    output = highlight_chunks_in_pdf(pdf_path=tmp_pdf, documents=[doc])
    assert os.path.exists(output)
    cleanup_file(output)


def test_highlight_chunks_skips_empty_page_content(tmp_pdf):
    doc = Document(page_content="   ", metadata={"page": 0})
    output = highlight_chunks_in_pdf(pdf_path=tmp_pdf, documents=[doc])
    assert os.path.exists(output)
    cleanup_file(output)


def test_highlight_chunks_multiple_pages(tmp_pdf_multipage):
    documents = [
        Document(page_content="Page 0 content sample text", metadata={"page": 0}),
        Document(page_content="Page 1 content sample text", metadata={"page": 1}),
        Document(page_content="Page 2 content sample text", metadata={"page": 2}),
    ]
    output = highlight_chunks_in_pdf(pdf_path=tmp_pdf_multipage, documents=documents)
    assert os.path.exists(output)
    cleanup_file(output)
