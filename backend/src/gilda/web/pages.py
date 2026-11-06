from typing import Any

from datastar_py.litestar import DatastarResponse, ServerSentEventGenerator
from litestar import MediaType, Request, Response, post
from litestar.datastructures import Cookie
from litestar.exceptions import HTTPException
from litestar.status_codes import HTTP_404_NOT_FOUND

from gilda.errors import api_error_response
from gilda.web.rendering import LANGUAGE_COOKIE, LANGUAGES, fragment, read_signals_dict

_ONE_YEAR = 365 * 24 * 60 * 60


@post("/language", status_code=200)
async def choose_language(request: Request[Any, Any, Any]) -> DatastarResponse:
    signals = await read_signals_dict(request)
    language = signals.get("language")
    cookies = []
    if language in LANGUAGES:
        cookies.append(
            Cookie(
                key=LANGUAGE_COOKIE,
                value=language,
                max_age=_ONE_YEAR,
                samesite="lax",
                httponly=True,
            )
        )
    return DatastarResponse(
        ServerSentEventGenerator.execute_script("window.location.reload()"), cookies=cookies
    )


def not_found(request: Request[Any, Any, Any], exc: HTTPException) -> Response[Any]:
    """The Not found page, for a path outside the API that no screen or action answers."""
    path = request.url.path
    if path == "/api" or path.startswith("/api/"):
        return api_error_response(request, exc)
    return Response(
        fragment(request, "not_found.html"),
        status_code=HTTP_404_NOT_FOUND,
        media_type=MediaType.HTML,
    )
