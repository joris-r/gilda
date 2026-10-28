from typing import Any

from litestar import Request, Response
from litestar.exceptions import HTTPException
from litestar.types import ExceptionHandlersMap


def api_exception_handlers() -> ExceptionHandlersMap:
    """Answer API errors as {"error": "<message>"}."""

    def handle(request: Request[Any, Any, Any], exc: HTTPException) -> Response[dict[str, str]]:
        return Response({"error": exc.detail}, status_code=exc.status_code)

    return {HTTPException: handle}
