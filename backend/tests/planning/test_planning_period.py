from collections.abc import Callable
from typing import Any

import pytest

from tests.planning.conftest import Planning, create_association, settings_section, sign_up

UNKNOWN_ID = "00000000-0000-4000-8000-000000000000"
PERIOD = {"first": "2026-11-02", "last": "2026-11-25"}
SHOWN = "Mon 2 Nov 2026 – Wed 25 Nov 2026"  # noqa: RUF001  (the screen's en dash)


def period_shown(client: Any, slug: str) -> str:
    return settings_section(client, slug, "Planning period")


def test_put_api_planning_period_401_when_signed_out(client: Any) -> None:
    response = client.put(f"/api/associations/{UNKNOWN_ID}/planning-period", json=PERIOD)

    assert response.status_code == 401
    assert "error" in response.json()


def test_put_api_planning_period_404_when_not_a_member(
    client: Any, new_client: Callable[[], Any]
) -> None:
    sign_up(client, "Alice")
    association = create_association(client)
    other = new_client()
    sign_up(other, "Zoé")

    response = other.put(f"/api/associations/{association['id']}/planning-period", json=PERIOD)

    assert response.status_code == 404
    assert "error" in response.json()


def test_put_api_planning_period_sets_it(client: Any, new_client: Callable[[], Any]) -> None:
    planning = Planning(client, new_client)

    response = client.put(planning.path("planning-period"), json=PERIOD)

    assert response.status_code == 200
    assert response.json() == PERIOD
    assert SHOWN in period_shown(planning.bruno_client, planning.slug)


def test_put_api_planning_period_replaces_the_previous_one(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    client.put(planning.path("planning-period"), json=PERIOD)
    later = {"first": "2026-11-30", "last": "2026-12-20"}

    response = client.put(planning.path("planning-period"), json=later)

    assert response.status_code == 200
    shown = period_shown(client, planning.slug)
    assert "Mon 30 Nov 2026 – Sun 20 Dec 2026" in shown  # noqa: RUF001
    assert SHOWN not in shown


def test_put_api_planning_period_accepts_a_single_day(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    day = {"first": "2026-11-02", "last": "2026-11-02"}

    response = client.put(planning.path("planning-period"), json=day)

    assert response.status_code == 200
    assert response.json() == day


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


def test_put_api_planning_period_403_for_a_volunteer(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    client.put(planning.path("planning-period"), json=PERIOD)

    later = {"first": "2026-12-01", "last": "2026-12-02"}
    response = planning.bruno_client.put(planning.path("planning-period"), json=later)

    assert response.status_code == 403
    assert SHOWN in period_shown(client, planning.slug)
