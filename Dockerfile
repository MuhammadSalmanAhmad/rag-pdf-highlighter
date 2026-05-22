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

# Expose the port Uvicorn will listen on
EXPOSE 8000

# Run with Uvicorn
CMD ["uvicorn", "rag_pdf_highlighter.main:app", "--host", "0.0.0.0", "--port", "8000"]
