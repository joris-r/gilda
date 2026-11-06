from typing import Any

from litestar import Request, Response
from litestar.exceptions import HTTPException
from litestar.types import ExceptionHandlersMap


def api_error_response(
    request: Request[Any, Any, Any], exc: HTTPException
) -> Response[dict[str, str]]:
    """Answer an API error as {"error": "<message>"}."""
    return Response({"error": exc.detail}, status_code=exc.status_code)


def api_exception_handlers() -> ExceptionHandlersMap:
    return {HTTPException: api_error_response}
