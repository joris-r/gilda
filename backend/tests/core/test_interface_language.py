from typing import Any

import pytest

FRENCH = "Se connecter"
ENGLISH = "Sign in"


class TestLanguage:
    @pytest.mark.parametrize(
        ("header", "expected"),
        [
            ("fr", FRENCH),
            ("fr-CA,fr;q=0.9,en;q=0.8", FRENCH),
            ("en;q=0.5,fr;q=0.8", FRENCH),
            ("de,fr;q=0.8", FRENCH),
            ("en", ENGLISH),
            ("en,fr;q=0.5", ENGLISH),
            ("de", ENGLISH),
        ],
    )
    def test_opens_in_french_when_the_browser_prefers_french(
        self, client: Any, header: str, expected: str
    ) -> None:
        page = client.get("/", headers={"Accept-Language": header}).text

        assert expected in page
        assert (FRENCH in page) == (expected == FRENCH)

    def test_opens_in_english_without_a_browser_preference(self, client: Any) -> None:
        page = client.get("/").text

        assert ENGLISH in page
        assert FRENCH not in page

    @pytest.mark.parametrize(
        ("cookie", "header", "expected"),
        [
            ("fr", "en", FRENCH),
            ("en", "fr", ENGLISH),
        ],
    )
    def test_the_language_cookie_wins_over_the_browser(
        self, client: Any, cookie: str, header: str, expected: str
    ) -> None:
        client.cookies.set("language", cookie)

        page = client.get("/", headers={"Accept-Language": header}).text

        assert expected in page
        assert (FRENCH in page) == (expected == FRENCH)

    def test_an_unknown_cookie_value_falls_back_to_the_browser(self, client: Any) -> None:
        client.cookies.set("language", "de")

        page = client.get("/", headers={"Accept-Language": "fr"}).text

        assert FRENCH in page
