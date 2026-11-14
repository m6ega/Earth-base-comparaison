"""Structured errors that map to the API contract's error shape."""

from __future__ import annotations


class TerraError(Exception):
    """A user-facing failure: no result is produced.

    ``code`` and ``message`` are returned to the client as
    ``{"status": "error", "error": {"code": ..., "message": ...}}``.
    Messages must never contain server paths or stack traces.
    """

    def __init__(self, code: str, message: str, http_status: int = 422) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


# Proposed error codes (docs/api-contract.md leaves the full list unresolved).
UNKNOWN_REFERENCE = ("UNKNOWN_REFERENCE", 400)
MISSING_FIELD = ("MISSING_FIELD", 422)
FILE_TOO_LARGE = ("FILE_TOO_LARGE", 413)
RASTER_TOO_LARGE = ("RASTER_TOO_LARGE", 413)
UNSUPPORTED_FORMAT = ("UNSUPPORTED_FORMAT", 415)
INVALID_DEM = ("INVALID_DEM", 422)
MISSING_CRS = ("MISSING_CRS", 422)
UNSUPPORTED_CRS = ("UNSUPPORTED_CRS", 422)
UNKNOWN_VERTICAL_UNITS = ("UNKNOWN_VERTICAL_UNITS", 422)
INSUFFICIENT_EXTENT = ("INSUFFICIENT_EXTENT", 422)
INSUFFICIENT_VALID_DATA = ("INSUFFICIENT_VALID_DATA", 422)
REFERENCE_UNAVAILABLE = ("REFERENCE_UNAVAILABLE", 500)
PROCESSING_FAILED = ("PROCESSING_FAILED", 500)


def fail(kind: tuple[str, int], message: str) -> TerraError:
    code, status = kind
    return TerraError(code, message, status)
