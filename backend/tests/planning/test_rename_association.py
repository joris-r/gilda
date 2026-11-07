from collections.abc import Callable
from typing import Any

from tests.core.conftest import rename_association, shown
from tests.planning.conftest import Planning


def test_rename_the_association_share_link_keeps_working_and_shows_the_new_name(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    share_link = client.post(planning.path("share-link"))
    assert share_link.status_code == 201, share_link.text
    token = share_link.json()["token"]

    text = shown(rename_association(client, planning.association["slug"], "Jardin des Lilas"))

    assert "The association is now Jardin des Lilas." in text
    shared = new_client().get(f"/api/shared/{token}")
    assert shared.status_code == 200
    assert shared.json()["name"] == "Jardin des Lilas"
