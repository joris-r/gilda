from collections.abc import Callable
from typing import Any

from tests.planning.conftest import Planning


# /planning/operations/get-shared-association/shared /core/operations/update-association/renamed
def test_patch_api_association_share_link_keeps_working_and_shows_the_new_name(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    share_link = client.post(planning.path("share-link"))
    assert share_link.status_code == 201, share_link.text
    token = share_link.json()["token"]

    response = client.patch(f"/api/associations/{planning.id}", json={"name": "Jardin des Lilas"})

    assert response.status_code == 200
    shared = new_client().get(f"/api/shared/{token}")
    assert shared.status_code == 200
    assert shared.json()["name"] == "Jardin des Lilas"
