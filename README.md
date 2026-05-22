# RAG PDF Highlighter

Highlight text chunks inside PDF documents — built for RAG pipelines.

Given a PDF URL and a list of text chunks (with page numbers), this service locates each chunk in the PDF and returns an annotated copy with highlights applied.

## Features

- **3-tier text matching** — exact → sentence → collapsed-whitespace fallback
- **Async PDF download** — non-blocking I/O via `httpx`
- **Stateless** — temp files are cleaned up after every request
- **Docker-ready** — single-command container deployment
- **Library-friendly** — core logic raises plain Python exceptions, no FastAPI dependency required

## Installation

```bash
pip install callisto-pdf-highlighter
```

Or install from source:

```bash
git clone https://github.com/RipeSeed/calli-pdf-highlighter-.git
cd calli-pdf-highlighter-
pip install -e ".[dev]"
```

## Quick Start

### As a microservice

```bash
uvicorn rag_pdf_highlighter.main:app --host 0.0.0.0 --port 8000
```

Then send a POST request:

```bash
curl -X POST http://localhost:8000/highlight \
  -H "Content-Type: application/json" \
  -d '{
    "pdf_url": "https://example.com/report.pdf",
    "documents": [
      {
        "page_content": "Text to highlight in the PDF",
        "metadata": {"page": 0}
      }
    ]
  }' \
  --output highlighted.pdf
```

### With Docker

```bash
docker build -t rag-pdf-highlighter .
docker run -p 8000:8000 rag-pdf-highlighter
```

### As a library

```python
from langchain_core.documents import Document
from rag_pdf_highlighter.utils.pdf_helpers import highlight_chunks_in_pdf

documents = [
    Document(page_content="Text to find", metadata={"page": 0}),
]

output_path = highlight_chunks_in_pdf(
    pdf_path="./report.pdf",
    documents=documents,
)
print(f"Highlighted PDF saved to: {output_path}")
```

## API Reference

### `GET /`

Health check endpoint.

### `POST /highlight`

| Field | Type | Description |
|-------|------|-------------|
| `pdf_url` | `string` | URL of the PDF to highlight |
| `documents` | `array` | List of `{page_content, metadata}` objects |
| `documents[].page_content` | `string` | The text chunk to locate and highlight |
| `documents[].metadata.page` | `int` | Zero-indexed page number |

**Returns:** The highlighted PDF file (`application/pdf`).

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check src/ test/
```

## License

[MIT](LICENSE.txt)
