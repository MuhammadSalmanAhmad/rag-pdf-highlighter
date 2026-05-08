import os
import tempfile

import fitz
import pytest


@pytest.fixture
def tmp_pdf(tmp_path):
    """Creates a minimal single-page PDF with known text content."""
    pdf_path = str(tmp_path / "sample.pdf")
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Hello world this is a test document")
    doc.save(pdf_path)
    doc.close()
    return pdf_path


@pytest.fixture
def tmp_pdf_multipage(tmp_path):
    """Creates a 3-page PDF with distinct text on each page."""
    pdf_path = str(tmp_path / "multipage.pdf")
    doc = fitz.open()
    for i in range(3):
        page = doc.new_page()
        page.insert_text((72, 72), f"Page {i} content sample text")
    doc.save(pdf_path)
    doc.close()
    return pdf_path
