import uuid
from collections.abc import Callable
from datetime import UTC, date, datetime
from typing import Any
from zoneinfo import ZoneInfo

import pytest
import time_machine

from tests.planning.conftest import WEEKDAYS, Planning, create_association, day_of_week

UNKNOWN_ID = "00000000-0000-4000-8000-000000000000"


def thursday_planning(client: Any, new_client: Callable[[], Any]) -> tuple[Planning, str]:
    """A planning with a slot on Thursday 10:00-13:00, and next week's Thursday."""
    planning = Planning(client, new_client)
    planning.add_slot("thursday", "10:00", "13:00")
    return planning, day_of_week("thursday")


# POST /api/associations/{id}/registrations


def test_r5_a_volunteer_registering_themself_is_confirmed(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning, thursday = thursday_planning(client, new_client)

    response = planning.register(planning.bruno_client, planning.bruno, thursday, "10:00", "13:00")

    assert response.status_code == 201
    body = response.json()
    assert body == {
        "id": body["id"],
        "user_id": planning.bruno["id"],
        "display_name": "Bruno",
        "status": "confirmed",
        "date": thursday,
        "start": "10:00",
        "end": "13:00",
    }
    uuid.UUID(body["id"])


def test_r5_a_manager_registering_themself_is_confirmed(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning, thursday = thursday_planning(client, new_client)

    response = planning.register(client, planning.alice, thursday, "10:00", "13:00")

    assert response.status_code == 201
    assert response.json()["status"] == "confirmed"


def test_r5_a_manager_registering_another_member_proposes(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning, thursday = thursday_planning(client, new_client)

    response = planning.register(client, planning.bruno, thursday, "10:00", "13:00")

    assert response.status_code == 201
    assert (response.json()["display_name"], response.json()["status"]) == ("Bruno", "proposed")


def test_r5_a_volunteer_registering_another_member_403(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning, thursday = thursday_planning(client, new_client)

    response = planning.register(planning.bruno_client, planning.chloe, thursday, "10:00", "13:00")

    assert response.status_code == 403
    assert "error" in response.json()
    assert planning.schedule(client, thursday, thursday)["occurrences"][0]["registration"] is None


def test_r4_409_when_the_occurrence_already_holds_a_registration(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning, thursday = thursday_planning(client, new_client)
    planning.registered(planning.bruno_client, planning.bruno, thursday, "10:00", "13:00")

    response = planning.register(planning.chloe_client, planning.chloe, thursday, "10:00", "13:00")

    assert response.status_code == 409
    assert "error" in response.json()


def test_r4_409_also_for_a_proposed_registration(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning, thursday = thursday_planning(client, new_client)
    planning.registered(client, planning.bruno, thursday, "10:00", "13:00")

    response = planning.register(planning.chloe_client, planning.chloe, thursday, "10:00", "13:00")

    assert response.status_code == 409


def test_r4_an_occurrence_whose_registration_was_cancelled_takes_a_new_one(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning, thursday = thursday_planning(client, new_client)
    first = planning.registered(planning.bruno_client, planning.bruno, thursday, "10:00", "13:00")
    planning.set_status(planning.bruno_client, first, "cancelled")

    response = planning.register(planning.chloe_client, planning.chloe, thursday, "10:00", "13:00")

    assert response.status_code == 201


@pytest.mark.parametrize(
    ("weekday", "start", "end"),
    [
        ("friday", "10:00", "13:00"),
        ("thursday", "10:00", "12:00"),
        ("thursday", "09:00", "13:00"),
    ],
)
def test_post_api_registrations_409_when_no_occurrence_matches(
    client: Any, new_client: Callable[[], Any], weekday: str, start: str, end: str
) -> None:
    planning, _ = thursday_planning(client, new_client)

    response = planning.register(
        planning.bruno_client, planning.bruno, day_of_week(weekday), start, end
    )

    assert response.status_code == 409
    assert "error" in response.json()


def test_post_api_registrations_409_on_a_closure_date(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning, thursday = thursday_planning(client, new_client)
    planning.add_closure(thursday, thursday)

    response = planning.register(planning.bruno_client, planning.bruno, thursday, "10:00", "13:00")

    assert response.status_code == 409


def test_post_api_registrations_409_on_a_slot_of_another_association(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    other = create_association(client, "Repair Café Belleville")
    client.post(
        f"/api/associations/{other['id']}/slots",
        json={"weekday": "thursday", "start": "10:00", "end": "13:00"},
    )

    response = planning.register(
        planning.bruno_client, planning.bruno, day_of_week("thursday"), "10:00", "13:00"
    )

    assert response.status_code == 409


def test_r6_409_when_the_date_is_before_today(client: Any, new_client: Callable[[], Any]) -> None:
    planning, _ = thursday_planning(client, new_client)

    response = planning.register(
        planning.bruno_client, planning.bruno, day_of_week("thursday", -1), "10:00", "13:00"
    )

    assert response.status_code == 409
    assert "error" in response.json()


def test_r6_today_is_not_before_today(client: Any, new_client: Callable[[], Any]) -> None:
    planning = Planning(client, new_client)
    today = datetime.now(ZoneInfo("Europe/Paris")).date()
    planning.add_slot(WEEKDAYS[today.weekday()], "23:00", "23:30")

    response = planning.register(
        planning.bruno_client, planning.bruno, today.isoformat(), "23:00", "23:30"
    )

    assert response.status_code == 201


@pytest.mark.parametrize(
    ("now", "day", "status"),
    [
        # Summer: 00:30 on 1 July in Paris (UTC+2), still 30 June in UTC.
        (datetime(2026, 6, 30, 22, 30, tzinfo=UTC), date(2026, 6, 30), 409),
        (datetime(2026, 6, 30, 22, 30, tzinfo=UTC), date(2026, 7, 1), 201),
        # Winter: 00:30 on 1 January in Paris (UTC+1), still 31 December in UTC.
        (datetime(2026, 12, 31, 23, 30, tzinfo=UTC), date(2026, 12, 31), 409),
        (datetime(2026, 12, 31, 23, 30, tzinfo=UTC), date(2027, 1, 1), 201),
        # 23:30 on 31 December in Paris: still today.
        (datetime(2026, 12, 31, 22, 30, tzinfo=UTC), date(2026, 12, 31), 201),
    ],
)
def test_r11_r6_today_is_in_the_associations_timezone(
    client: Any, new_client: Callable[[], Any], now: datetime, day: date, status: int
) -> None:
    with time_machine.travel(now, tick=False):
        planning = Planning(client, new_client)
        planning.add_slot(WEEKDAYS[day.weekday()], "10:00", "13:00")

        response = planning.register(
            planning.bruno_client, planning.bruno, day.isoformat(), "10:00", "13:00"
        )

    assert response.status_code == status, response.text


def test_post_api_registrations_400_when_the_user_is_not_a_member(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning, thursday = thursday_planning(client, new_client)

    response = planning.register(client, {"id": UNKNOWN_ID}, thursday, "10:00", "13:00")

    assert response.status_code == 400
    assert "error" in response.json()


@pytest.mark.parametrize("missing", ["user_id", "date", "start", "end"])
def test_post_api_registrations_400_when_a_field_is_missing(
    client: Any, new_client: Callable[[], Any], missing: str
) -> None:
    planning, thursday = thursday_planning(client, new_client)
    body = {"user_id": planning.alice["id"], "date": thursday, "start": "10:00", "end": "13:00"}
    del body[missing]

    response = client.post(planning.path("registrations"), json=body)

    assert response.status_code == 400
    assert "error" in response.json()


# PATCH /api/associations/{id}/registrations/{registration_id}


def proposed_to_bruno(client: Any, new_client: Callable[[], Any]) -> tuple[Planning, Any]:
    planning, thursday = thursday_planning(client, new_client)
    return planning, planning.registered(client, planning.bruno, thursday, "10:00", "13:00")


def test_r7_the_registered_user_confirms_a_proposed_registration(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning, registration = proposed_to_bruno(client, new_client)

    response = planning.set_status(planning.bruno_client, registration, "confirmed")

    assert response.status_code == 200
    assert response.json() == {**registration, "status": "confirmed"}


def test_r7_a_manager_confirms_another_members_proposed_registration(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning, registration = proposed_to_bruno(client, new_client)

    response = planning.set_status(client, registration, "confirmed")

    assert response.status_code == 200
    assert response.json() == {**registration, "status": "confirmed"}


def test_r7_nobody_else_confirms(client: Any, new_client: Callable[[], Any]) -> None:
    planning, registration = proposed_to_bruno(client, new_client)

    response = planning.set_status(planning.chloe_client, registration, "confirmed")

    assert response.status_code == 403
    assert "error" in response.json()


def test_r7_confirming_a_confirmed_registration_409(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning, thursday = thursday_planning(client, new_client)
    registration = planning.registered(
        planning.bruno_client, planning.bruno, thursday, "10:00", "13:00"
    )

    response = planning.set_status(planning.bruno_client, registration, "confirmed")

    assert response.status_code == 409
    assert "error" in response.json()


def test_r7_confirming_a_cancelled_registration_409(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning, registration = proposed_to_bruno(client, new_client)
    planning.set_status(planning.bruno_client, registration, "cancelled")

    response = planning.set_status(planning.bruno_client, registration, "confirmed")

    assert response.status_code == 409


def test_r7_confirming_an_obsolete_registration_409(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning, registration = proposed_to_bruno(client, new_client)
    slot = client.get(planning.path("slots")).json()[0]
    client.delete(planning.path(f"slots/{slot['id']}"))

    response = planning.set_status(planning.bruno_client, registration, "confirmed")

    assert response.status_code == 409


def test_r7_a_manager_confirming_an_obsolete_registration_409(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning, registration = proposed_to_bruno(client, new_client)
    slot = client.get(planning.path("slots")).json()[0]
    client.delete(planning.path(f"slots/{slot['id']}"))

    response = planning.set_status(client, registration, "confirmed")

    assert response.status_code == 409


def test_r7_the_registered_user_cancels(client: Any, new_client: Callable[[], Any]) -> None:
    planning, thursday = thursday_planning(client, new_client)
    registration = planning.registered(
        planning.bruno_client, planning.bruno, thursday, "10:00", "13:00"
    )

    response = planning.set_status(planning.bruno_client, registration, "cancelled")

    assert response.status_code == 200
    assert response.json() == {**registration, "status": "cancelled"}


def test_r7_a_manager_cancels_another_members_registration(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning, thursday = thursday_planning(client, new_client)
    registration = planning.registered(
        planning.bruno_client, planning.bruno, thursday, "10:00", "13:00"
    )

    response = planning.set_status(client, registration, "cancelled")

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


def test_r7_an_obsolete_registration_can_be_cancelled(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning, registration = proposed_to_bruno(client, new_client)
    slot = client.get(planning.path("slots")).json()[0]
    client.delete(planning.path(f"slots/{slot['id']}"))

    response = planning.set_status(planning.bruno_client, registration, "cancelled")

    assert response.status_code == 200


def test_r7_another_volunteer_cannot_cancel(client: Any, new_client: Callable[[], Any]) -> None:
    planning, thursday = thursday_planning(client, new_client)
    registration = planning.registered(
        planning.bruno_client, planning.bruno, thursday, "10:00", "13:00"
    )

    response = planning.set_status(planning.chloe_client, registration, "cancelled")

    assert response.status_code == 403
    thursday_schedule = planning.schedule(client, thursday, thursday)
    assert thursday_schedule["occurrences"][0]["registration"]["status"] == "confirmed"


def test_r7_cancelling_a_cancelled_registration_409(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning, registration = proposed_to_bruno(client, new_client)
    planning.set_status(client, registration, "cancelled")

    response = planning.set_status(client, registration, "cancelled")

    assert response.status_code == 409


def test_r7_back_to_proposed_409(client: Any, new_client: Callable[[], Any]) -> None:
    planning, thursday = thursday_planning(client, new_client)
    registration = planning.registered(
        planning.bruno_client, planning.bruno, thursday, "10:00", "13:00"
    )

    response = planning.set_status(planning.bruno_client, registration, "proposed")

    assert response.status_code == 409


def test_patch_api_registration_400_when_the_status_is_invalid(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning, registration = proposed_to_bruno(client, new_client)

    response = planning.set_status(planning.bruno_client, registration, "done")

    assert response.status_code == 400
    assert "error" in response.json()


def test_patch_api_registration_404_when_not_of_this_association(
    client: Any, new_client: Callable[[], Any]
) -> None:
    _, registration = proposed_to_bruno(client, new_client)
    other = create_association(client, "Repair Café Belleville")

    response = client.patch(
        f"/api/associations/{other['id']}/registrations/{registration['id']}",
        json={"status": "cancelled"},
    )

    assert response.status_code == 404
    assert "error" in response.json()


def test_patch_api_registration_404_when_unknown(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning, _ = thursday_planning(client, new_client)

    response = planning.set_status(client, {"id": UNKNOWN_ID}, "cancelled")

    assert response.status_code == 404
