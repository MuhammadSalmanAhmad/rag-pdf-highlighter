"""
exceptions.py
~~~~~~~~~~~~~
Custom exception hierarchy for the PDF highlighter service.

These are plain Python exceptions (no FastAPI dependency) so the
highlighting logic can be used as a standalone library.
"""


class HighlightError(Exception):
    """Base exception for all highlighting errors."""


class PDFDownloadError(HighlightError):
    """Raised when a PDF cannot be downloaded from the given URL."""


class PDFNotFoundError(HighlightError):
    """Raised when the specified PDF file does not exist on disk."""


class NoDocumentsError(HighlightError):
    """Raised when an empty document list is passed to the highlighter."""
