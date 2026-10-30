from collections.abc import Callable
from typing import Any

import pytest

from tests.planning.conftest import Planning, create_association, sign_up

UNKNOWN_ID = "00000000-0000-4000-8000-000000000000"
PERIOD = {"first": "2026-11-02", "last": "2026-11-25"}


@pytest.mark.parametrize(("method", "body"), [("GET", None), ("PUT", PERIOD), ("DELETE", None)])
def test_planning_period_401_when_signed_out(
    client: Any, method: str, body: dict[str, str] | None
) -> None:
    response = client.request(method, f"/api/associations/{UNKNOWN_ID}/planning-period", json=body)

    assert response.status_code == 401
    assert "error" in response.json()


@pytest.mark.parametrize(("method", "body"), [("GET", None), ("PUT", PERIOD), ("DELETE", None)])
def test_planning_period_404_when_not_a_member(
    client: Any, new_client: Callable[[], Any], method: str, body: dict[str, str] | None
) -> None:
    sign_up(client, "Alice")
    association = create_association(client)
    other = new_client()
    sign_up(other, "Zoé")

    response = other.request(
        method, f"/api/associations/{association['id']}/planning-period", json=body
    )

    assert response.status_code == 404
    assert "error" in response.json()


def test_put_api_planning_period_sets_it(client: Any, new_client: Callable[[], Any]) -> None:
    planning = Planning(client, new_client)

    response = client.put(planning.path("planning-period"), json=PERIOD)

    assert response.status_code == 200
    assert response.json() == PERIOD
    assert planning.bruno_client.get(planning.path("planning-period")).json() == PERIOD


def test_put_api_planning_period_replaces_the_previous_one(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    client.put(planning.path("planning-period"), json=PERIOD)
    later = {"first": "2026-11-30", "last": "2026-12-20"}

    response = client.put(planning.path("planning-period"), json=later)

    assert response.status_code == 200
    assert client.get(planning.path("planning-period")).json() == later


def test_put_api_planning_period_accepts_a_single_day(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    day = {"first": "2026-11-02", "last": "2026-11-02"}

    response = client.put(planning.path("planning-period"), json=day)

    assert response.status_code == 200
    assert response.json() == day


def test_get_api_planning_period_null_when_there_is_none(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)

    response = planning.bruno_client.get(planning.path("planning-period"))

    assert response.status_code == 200
    assert response.json() is None


def test_delete_api_planning_period_removes_it(client: Any, new_client: Callable[[], Any]) -> None:
    planning = Planning(client, new_client)
    client.put(planning.path("planning-period"), json=PERIOD)

    response = client.delete(planning.path("planning-period"))

    assert response.status_code == 204
    assert client.get(planning.path("planning-period")).json() is None


@pytest.mark.parametrize(
    "body",
    [
        {"first": "2026-11-25", "last": "2026-11-02"},
        {"first": "2026-11-02"},
        {"last": "2026-11-25"},
        {"first": "2 Nov", "last": "2026-11-25"},
    ],
)
def test_put_api_planning_period_400_when_a_field_is_missing_or_invalid(
    client: Any, new_client: Callable[[], Any], body: dict[str, str]
) -> None:
    planning = Planning(client, new_client)

    response = client.put(planning.path("planning-period"), json=body)

    assert response.status_code == 400
    assert "error" in response.json()


def test_planning_period_403_for_a_volunteer(client: Any, new_client: Callable[[], Any]) -> None:
    planning = Planning(client, new_client)
    client.put(planning.path("planning-period"), json=PERIOD)
    bruno = planning.bruno_client

    later = {"first": "2026-12-01", "last": "2026-12-02"}
    put = bruno.put(planning.path("planning-period"), json=later)
    deleted = bruno.delete(planning.path("planning-period"))

    assert (put.status_code, deleted.status_code) == (403, 403)
    assert client.get(planning.path("planning-period")).json() == PERIOD
