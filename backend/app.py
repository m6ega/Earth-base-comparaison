"""Terra Analog FastAPI application.

Run from backend/:  uvicorn app:app --reload
Routes only translate HTTP to the pure pipeline in analysis.py.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

import analysis
import errors
import settings
from reference import REFERENCE_DIRS, list_references, load_reference
from validation import check_extension, save_upload

logger = logging.getLogger("terra")


def error_response(code: str, message: str, status: int) -> JSONResponse:
    return JSONResponse(status_code=status, content={"status": "error", "error": {"code": code, "message": message}})


class RequestSizeLimitMiddleware:
    """Reject oversized POST /analyze bodies before the multipart parser sees them.

    Checks Content-Length when present, and counts streamed (chunked) bytes
    otherwise. The body is buffered to a spooled temporary file (1 MiB in
    memory, then disk) and replayed to the application only if it fits.
    """

    def __init__(self, app, max_bytes: int, path: str = "/analyze") -> None:
        self.app = app
        self.max_bytes = max_bytes
        self.path = path

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] != "POST" or scope["path"] != self.path:
            await self.app(scope, receive, send)
            return

        code, status = errors.FILE_TOO_LARGE
        too_large = error_response(
            code, f"The upload exceeds the {settings.MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit.", status
        )
        headers = dict(scope.get("headers") or [])
        length = headers.get(b"content-length")
        if length is not None:
            try:
                if int(length) > self.max_bytes:
                    await too_large(scope, receive, send)
                    return
            except ValueError:
                await error_response("INVALID_REQUEST", "Invalid Content-Length header.", 400)(scope, receive, send)
                return

        spool = tempfile.SpooledTemporaryFile(max_size=1024 * 1024)
        try:
            total = 0
            more = True
            while more:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                body = message.get("body", b"")
                total += len(body)
                if total > self.max_bytes:
                    await too_large(scope, receive, send)
                    return
                spool.write(body)
                more = message.get("more_body", False)
            spool.seek(0)

            done = False

            async def replay():
                nonlocal done
                if done:
                    return {"type": "http.disconnect"}
                chunk = spool.read(settings.UPLOAD_CHUNK_BYTES)
                more_body = spool.tell() < total
                if not more_body:
                    done = True
                return {"type": "http.request", "body": chunk, "more_body": more_body}

            await self.app(scope, replay, send)
        finally:
            spool.close()


app = FastAPI(title="Terra Analog API", version=settings.METHODOLOGY_VERSION)
# Added first = inner: CORS (outermost) also decorates 413 responses.
app.add_middleware(RequestSizeLimitMiddleware, max_bytes=settings.MAX_REQUEST_BODY_BYTES)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.exception_handler(errors.TerraError)
async def terra_error_handler(_: Request, exc: errors.TerraError):
    if exc.http_status >= 500:
        logger.error("Processing error %s: %s", exc.code, exc.message, exc_info=exc.__cause__)
    return error_response(exc.code, exc.message, exc.http_status)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError):
    return error_response("INVALID_REQUEST", "The request is malformed or missing required fields.", 422)


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(_: Request, exc: StarletteHTTPException):
    code = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}.get(exc.status_code, "HTTP_ERROR")
    message = exc.detail if isinstance(exc.detail, str) else "Request failed."
    return error_response(code, message, exc.status_code)


@app.exception_handler(Exception)
async def unexpected_error_handler(_: Request, exc: Exception):
    logger.exception("Unexpected failure")
    return error_response("PROCESSING_FAILED", "An unexpected error occurred while processing the request.", 500)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/references")
def references():
    return {"is_mock": False, "references": [r.api_object() for r in list_references()]}


@app.get("/static/references/{reference_id}/preview.png", include_in_schema=False)
def reference_preview(reference_id: str):
    # Only registered references; never arbitrary paths. The DEM itself is not served.
    if reference_id not in REFERENCE_DIRS:
        return error_response("NOT_FOUND", "Unknown reference preview.", 404)
    return FileResponse(load_reference(reference_id).preview_path, media_type="image/png")


@app.post("/analyze")
def analyze(file: UploadFile | None = File(None), reference_id: str | None = Form(None)):
    if file is None or not file.filename:
        raise errors.fail(errors.MISSING_FIELD, "The 'file' field with an Earth GeoTIFF is required.")
    if not reference_id:
        raise errors.fail(errors.MISSING_FIELD, "The 'reference_id' field is required.")
    if reference_id not in REFERENCE_DIRS:
        raise errors.fail(errors.UNKNOWN_REFERENCE, f"Unknown reference_id '{reference_id}'.")
    check_extension(file.filename)
    with tempfile.TemporaryDirectory(prefix="terra-") as tmp:
        # Fixed name: the client filename is never used as a path.
        path = Path(tmp) / "upload.tif"
        save_upload(file.file, path)
        return analysis.analyze(path, reference_id)
