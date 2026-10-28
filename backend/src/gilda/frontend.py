import os
from pathlib import Path
from typing import Any

from litestar import Request, Response, Router
from litestar.exceptions import NotFoundException
from litestar.response import File
from litestar.static_files import create_static_files_router
from litestar.types import ExceptionHandlersMap


def create_frontend_router() -> Router | None:
    """Serve the built frontend from GILDA_FRONTEND_DIR, if set."""
    directory = _frontend_dir()
    if directory is None:
        return None
    return create_static_files_router(path="/", directories=[directory], html_mode=True)


def frontend_exception_handlers() -> ExceptionHandlersMap:
    """Answer unknown paths outside /api with index.html, for the frontend router."""
    directory = _frontend_dir()
    if directory is None:
        return {}
    index = directory / "index.html"

    def not_found(request: Request[Any, Any, Any], exc: NotFoundException) -> Response[object]:
        if request.url.path.startswith("/api"):
            return Response({"status_code": 404, "detail": "Not Found"}, status_code=404)
        return File(index, media_type="text/html", content_disposition_type="inline")

    return {NotFoundException: not_found}


def _frontend_dir() -> Path | None:
    value = os.environ.get("GILDA_FRONTEND_DIR")
    return Path(value).resolve() if value else None
