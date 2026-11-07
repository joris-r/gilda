import json
from pathlib import Path
from typing import Any, cast

from litestar import Request
from litestar.response import Template
from litestar.template import TemplateProtocol

from gilda.mailer import Language, preferred_language

LANGUAGE_COOKIE = "language"
LANGUAGES: tuple[Language, ...] = ("en", "fr")
_NOTICE_KEY = "notice"

_LOCALES = Path(__file__).parent / "locales"
_TRANSLATIONS: dict[str, dict[str, Any]] = {
    language: json.loads((_LOCALES / f"{language}.json").read_text(encoding="utf-8"))
    for language in LANGUAGES
}


def interface_language(request: Request[Any, Any, Any]) -> Language:
    """The language cookie, then the browser's preference."""
    chosen = request.cookies.get(LANGUAGE_COOKIE)
    for language in LANGUAGES:
        if language == chosen:
            return language
    return preferred_language(request.headers.get("accept-language"))


def translate(language: Language, key: str, **values: object) -> str:
    """The text of a dotted key, e.g. "signIn.title", with its `{name}` values filled."""
    found: Any = _TRANSLATIONS[language]
    for part in key.split("."):
        found = found[part]
    text = cast("str", found)
    for name, value in values.items():
        text = text.replace(f"{{{name}}}", str(value))
    return text


def _context(request: Request[Any, Any, Any], context: dict[str, Any]) -> dict[str, Any]:
    language = interface_language(request)

    def t(key: str, **values: object) -> str:
        return translate(language, key, **values)

    return {"language": language, "t": t, **context}


def flash(request: Request[Any, Any, Any], message: str) -> None:
    """Keeps `message` for the next page the user opens, which shows it as its notice."""
    request.set_session({**(request.session or {}), _NOTICE_KEY: message})


def page(request: Request[Any, Any, Any], template: str, **context: Any) -> Template:
    """A full page, with the notice kept for it, if any."""
    session = request.session or {}
    notice = session.get(_NOTICE_KEY, "")
    if notice:
        request.set_session({k: v for k, v in session.items() if k != _NOTICE_KEY})
    return Template(template, context=_context(request, {"notice": notice, **context}))


def fragment(request: Request[Any, Any, Any], template: str, **context: Any) -> str:
    """The HTML of a template, for a patch of the page."""
    engine = cast("Any", request.app.template_engine)
    found: TemplateProtocol = engine.get_template(template)
    return found.render(**_context(request, context))


async def read_signals_dict(request: Request[Any, Any, Any]) -> dict[str, Any]:
    """The Datastar signals of an action; none when its body is not a JSON object."""
    try:
        signals = json.loads(await request.body())
    except ValueError:
        return {}
    return signals if isinstance(signals, dict) else {}
