import html
import re
from collections.abc import Callable
from typing import Any

from tests.core.conftest import rename_association, shown
from tests.planning.conftest import Planning, part, shared_page, shared_token, text_of


def test_rename_the_association_share_link_keeps_working_and_shows_the_new_name(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    token = shared_token(planning)

    text = shown(rename_association(client, planning.association["slug"], "Jardin des Lilas"))

    assert "The association is now Jardin des Lilas." in text
    shared = shared_page(new_client(), token)
    assert shared.status_code == 200
    header = " ".join(text_of(part(html.unescape(shared.text), "header")).split())
    assert "Jardin des Lilas" in header
    assert "Jardin partagé des Lilas" not in header
    assert re.search(r"<h2[^>]*>\s*Week \d+\s*</h2>", shared.text)
