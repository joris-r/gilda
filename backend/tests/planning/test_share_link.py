from collections.abc import Callable
from typing import Any

import pytest

from tests.planning.conftest import Planning, create_association, day_of_week, sign_up

UNKNOWN_ID = "00000000-0000-4000-8000-000000000000"
PERIOD = {"first": "2026-11-02", "last": "2026-11-25"}


def create_share_link(planning: Planning) -> str:
    response = planning.alice_client.post(planning.path("share-link"))
    assert response.status_code == 201, response.text
    token: str = response.json()["token"]
    return token


# Share link


@pytest.mark.parametrize("method", ["GET", "POST", "DELETE"])
def test_share_link_401_when_signed_out(client: Any, method: str) -> None:
    response = client.request(method, f"/api/associations/{UNKNOWN_ID}/share-link")

    assert response.status_code == 401
    assert "error" in response.json()


@pytest.mark.parametrize("method", ["GET", "POST", "DELETE"])
def test_share_link_404_when_not_a_member(
    client: Any, new_client: Callable[[], Any], method: str
) -> None:
    sign_up(client, "Alice")
    association = create_association(client)
    other = new_client()
    sign_up(other, "Zoé")

    response = other.request(method, f"/api/associations/{association['id']}/share-link")

    assert response.status_code == 404
    assert "error" in response.json()


@pytest.mark.parametrize("method", ["GET", "POST", "DELETE"])
def test_share_link_403_for_a_volunteer(
    client: Any, new_client: Callable[[], Any], method: str
) -> None:
    planning = Planning(client, new_client)

    response = planning.bruno_client.request(method, planning.path("share-link"))

    assert response.status_code == 403
    assert "error" in response.json()


def test_get_share_link_is_null_when_there_is_none(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)

    response = client.get(planning.path("share-link"))

    assert response.status_code == 200
    assert response.json() is None


def test_post_share_link_creates_it(client: Any, new_client: Callable[[], Any]) -> None:
    planning = Planning(client, new_client)

    response = client.post(planning.path("share-link"))

    assert response.status_code == 201
    token = response.json()["token"]
    assert isinstance(token, str) and len(token) >= 20
    assert client.get(planning.path("share-link")).json() == {"token": token}


def test_share_links_of_two_associations_differ(client: Any, new_client: Callable[[], Any]) -> None:
    planning = Planning(client, new_client)
    other = Planning(new_client(), new_client)

    assert create_share_link(planning) != create_share_link(other)


def test_r33_creating_a_share_link_replaces_the_previous_one(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    previous = create_share_link(planning)

    token = create_share_link(planning)

    assert token != previous
    assert client.get(planning.path("share-link")).json() == {"token": token}
    assert new_client().get(f"/api/shared/{previous}").status_code == 404
    assert new_client().get(f"/api/shared/{token}").status_code == 200


def test_r33_revoking_the_share_link_deletes_it(client: Any, new_client: Callable[[], Any]) -> None:
    planning = Planning(client, new_client)
    token = create_share_link(planning)

    response = client.delete(planning.path("share-link"))

    assert response.status_code == 204
    assert client.get(planning.path("share-link")).json() is None
    assert new_client().get(f"/api/shared/{token}").status_code == 404
    assert new_client().get(f"/api/shared/{token}/schedule").status_code == 404


def test_delete_share_link_204_when_there_is_none(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)

    assert client.delete(planning.path("share-link")).status_code == 204


# Shared schedule


@pytest.mark.parametrize("path", ["", "/schedule"])
def test_shared_schedule_404_for_an_unknown_token(client: Any, path: str) -> None:
    response = client.get(f"/api/shared/unknown-token{path}")

    assert response.status_code == 404
    assert "error" in response.json()


def test_get_shared_returns_the_association_signed_out(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    client.put(planning.path("planning-period"), json=PERIOD)
    token = create_share_link(planning)

    response = new_client().get(f"/api/shared/{token}")

    assert response.status_code == 200
    assert response.json() == {
        "name": "Jardin partagé des Lilas",
        "timezone": "Europe/Paris",
        "planning_period": PERIOD,
    }


def test_get_shared_planning_period_is_null_when_there_is_none(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    token = create_share_link(planning)

    response = new_client().get(f"/api/shared/{token}")

    assert response.json()["planning_period"] is None


def test_get_shared_works_signed_in_as_a_non_member(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    token = create_share_link(planning)
    other = new_client()
    sign_up(other, "Zoé")

    assert other.get(f"/api/shared/{token}").status_code == 200
    assert other.get(f"/api/shared/{token}/schedule").status_code == 200


def _filled(planning: Planning) -> None:
    planning.add_slot("thursday", "10:00", "13:00")
    planning.add_slot("saturday", "10:00", "13:00")
    planning.registered(
        planning.bruno_client, planning.bruno, day_of_week("thursday"), "10:00", "13:00"
    )
    planning.registered(
        planning.alice_client, planning.chloe, day_of_week("saturday"), "10:00", "13:00"
    )
    planning.add_closure(day_of_week("saturday", 2), day_of_week("saturday", 2), "Fête")


def test_shared_schedule_returns_what_the_members_schedule_returns(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    _filled(planning)
    token = create_share_link(planning)
    first, last = day_of_week("monday", 1), day_of_week("sunday", 2)

    response = new_client().get(f"/api/shared/{token}/schedule", params={"from": first, "to": last})

    assert response.status_code == 200
    assert response.json() == planning.schedule(planning.bruno_client, first, last)


def test_shared_schedule_without_from_and_to_returns_the_default_range(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    _filled(planning)
    client.put(planning.path("planning-period"), json=PERIOD)
    token = create_share_link(planning)

    response = new_client().get(f"/api/shared/{token}/schedule")

    assert response.status_code == 200
    assert response.json() == planning.bruno_client.get(planning.path("schedule")).json()


def test_shared_schedule_400_when_only_one_of_from_and_to_is_given(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    token = create_share_link(planning)

    response = new_client().get(
        f"/api/shared/{token}/schedule", params={"from": day_of_week("monday")}
    )

    assert response.status_code == 400
    assert "error" in response.json()


def test_shared_schedule_shows_only_its_association(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    other = Planning(new_client(), new_client)
    other.add_slot("thursday", "10:00", "13:00")
    token = create_share_link(planning)

    response = new_client().get(
        f"/api/shared/{token}/schedule",
        params={"from": day_of_week("monday"), "to": day_of_week("sunday")},
    )

    assert response.json()["occurrences"] == []
