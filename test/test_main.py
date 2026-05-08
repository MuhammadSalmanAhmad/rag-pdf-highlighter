from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.main import app

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
    with patch("main.download_pdf", new_callable=AsyncMock, return_value=tmp_pdf):
        with patch("main.highlight_chunks_in_pdf", return_value=tmp_pdf):
            with patch("main.cleanup_file"):
                response = client.post("/highlight", json=VALID_PAYLOAD)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"] == 'attachment; filename="highlighted.pdf"'


def test_highlight_returns_400_on_download_failure():
    from fastapi import HTTPException

    with patch(
        "main.download_pdf",
        new_callable=AsyncMock,
        side_effect=HTTPException(status_code=400, detail="Failed to download PDF: connection refused"),
    ):
        response = client.post("/highlight", json=VALID_PAYLOAD)

    assert response.status_code == 400
    assert "Failed to download PDF" in response.json()["detail"]


def test_highlight_returns_400_on_empty_documents():
    from fastapi import HTTPException

    payload = {**VALID_PAYLOAD, "documents": []}

    with patch("main.download_pdf", new_callable=AsyncMock, return_value="/tmp/fake.pdf"):
        with patch(
            "main.highlight_chunks_in_pdf",
            side_effect=HTTPException(status_code=400, detail="No documents provided"),
        ):
            with patch("main.cleanup_file"):
                response = client.post("/highlight", json=payload)

    assert response.status_code == 400
    assert "No documents provided" in response.json()["detail"]


def test_highlight_returns_500_on_unexpected_error():
    with patch("main.download_pdf", new_callable=AsyncMock, side_effect=RuntimeError("unexpected")):
        response = client.post("/highlight", json=VALID_PAYLOAD)

    assert response.status_code == 500
    assert "Highlighting failed" in response.json()["detail"]


def test_highlight_invalid_payload_missing_pdf_url():
    response = client.post("/highlight", json={"documents": []})
    assert response.status_code == 422


def test_highlight_invalid_payload_missing_documents():
    response = client.post("/highlight", json={"pdf_url": "https://example.com/sample.pdf"})
    assert response.status_code == 422
