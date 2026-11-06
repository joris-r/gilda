from typing import Any

from datastar_py.litestar import DatastarResponse, ServerSentEventGenerator
from litestar import Request, post
from litestar.datastructures import Cookie

from gilda.web.rendering import LANGUAGE_COOKIE, LANGUAGES, read_signals_dict

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
