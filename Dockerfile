FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies required by PyMuPDF
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
    libmupdf-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy application code and install from pyproject.toml
COPY . .
RUN pip install --no-cache-dir .

ENV PORT=8000
EXPOSE 8000

# Run with Uvicorn — must bind 0.0.0.0, not 127.0.0.1
CMD ["sh", "-c", "exec uvicorn rag_pdf_highlighter.main:app --host 0.0.0.0 --port ${PORT}"]
