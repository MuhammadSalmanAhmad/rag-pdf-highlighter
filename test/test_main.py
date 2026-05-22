from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from rag_pdf_highlighter.exceptions import NoDocumentsError, PDFDownloadError
from rag_pdf_highlighter.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# GET /
# ---------------------------------------------------------------------------

def test_health_check():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok the app is running"}


# ---------------------------------------------------------------------------
# POST /highlight
# ---------------------------------------------------------------------------

VALID_PAYLOAD = {
    "pdf_url": "https://example.com/sample.pdf",
    "documents": [
        {"page_content": "Hello world this is a test document", "metadata": {"page": 0}}
    ],
}


def test_highlight_returns_pdf(tmp_pdf):
    with patch("rag_pdf_highlighter.main.download_pdf", new_callable=AsyncMock, return_value=tmp_pdf):
        with patch("rag_pdf_highlighter.main.highlight_chunks_in_pdf", return_value=tmp_pdf):
            with patch("rag_pdf_highlighter.main.cleanup_file"):
                response = client.post("/highlight", json=VALID_PAYLOAD)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"] == 'attachment; filename="highlighted.pdf"'


def test_highlight_returns_400_on_download_failure():
    with patch(
        "rag_pdf_highlighter.main.download_pdf",
        new_callable=AsyncMock,
        side_effect=PDFDownloadError("Failed to download PDF: connection refused"),
    ):
        response = client.post("/highlight", json=VALID_PAYLOAD)

    assert response.status_code == 400
    assert "Failed to download PDF" in response.json()["detail"]


def test_highlight_returns_400_on_empty_documents():
    payload = {**VALID_PAYLOAD, "documents": []}

    with patch("rag_pdf_highlighter.main.download_pdf", new_callable=AsyncMock, return_value="/tmp/fake.pdf"):
        with patch(
            "rag_pdf_highlighter.main.highlight_chunks_in_pdf",
            side_effect=NoDocumentsError("No documents provided"),
        ):
            with patch("rag_pdf_highlighter.main.cleanup_file"):
                response = client.post("/highlight", json=payload)

    assert response.status_code == 400
    assert "No documents provided" in response.json()["detail"]


def test_highlight_returns_500_on_unexpected_error():
    with patch("rag_pdf_highlighter.main.download_pdf", new_callable=AsyncMock, side_effect=RuntimeError("unexpected")):
        response = client.post("/highlight", json=VALID_PAYLOAD)

    assert response.status_code == 500
    assert "Highlighting failed" in response.json()["detail"]


def test_highlight_invalid_payload_missing_pdf_url():
    response = client.post("/highlight", json={"documents": []})
    assert response.status_code == 422


def test_highlight_invalid_payload_missing_documents():
    response = client.post("/highlight", json={"pdf_url": "https://example.com/sample.pdf"})
    assert response.status_code == 422
