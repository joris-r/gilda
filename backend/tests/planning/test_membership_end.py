import asyncio
import os
from collections.abc import Callable
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from tests.core.conftest import remove_member, shown
from tests.planning.conftest import (
    Planning,
    add_member,
    availability_lines,
    availability_section,
    day_of_week,
    preferences_stored,
    set_my_preference,
)

THURSDAY = ("10:00", "13:00")


def move_a_year_back(registration: dict[str, Any]) -> str:
    """Moves a registration 52 weeks back, to the same weekday, which the API cannot do."""

    async def run() -> str:
        engine = create_async_engine(os.environ["DATABASE_URL"])
        async with engine.begin() as connection:
            result = await connection.execute(
                text(
                    "UPDATE registration SET date = date - 364 WHERE id = :id RETURNING date::text"
                ),
                {"id": registration["id"]},
            )
            day: str = result.scalar_one()
        await engine.dispose()
        return day

    return asyncio.run(run())


def preferences_held(user: dict[str, Any]) -> int:
    """Counts the stored preferences of a user, which no screen shows once they are gone."""

    async def run() -> int:
        engine = create_async_engine(os.environ["DATABASE_URL"])
        async with engine.begin() as connection:
            result = await connection.execute(
                text("SELECT count(*) FROM preference WHERE user_id = :id"), {"id": user["id"]}
            )
            count: int = result.scalar_one()
        await engine.dispose()
        return count

    return asyncio.run(run())


def remove(planning: Planning, user: dict[str, Any]) -> None:
    slug = planning.association["slug"]
    assert "is removed." in shown(remove_member(planning.alice_client, slug, user["id"]))


def delete_account(client: Any) -> None:
    assert client.post("/delete-account").status_code == 200


def end_by_removal(planning: Planning) -> None:
    remove(planning, planning.bruno)


def end_by_account_deletion(planning: Planning) -> None:
    delete_account(planning.bruno_client)


ENDINGS = pytest.mark.parametrize(
    "end", [end_by_removal, end_by_account_deletion], ids=["removal", "account_deletion"]
)


def registration_on(planning: Planning, day: str) -> dict[str, Any] | None:
    body = planning.schedule(planning.alice_client, day, day)
    registration: dict[str, Any] | None = body["occurrences"][0]["registration"]
    return registration


def rejoin(planning: Planning) -> None:
    """Adds Bruno back after his removal; he is the same user (R3)."""
    response = add_member(planning.alice_client, planning.id, "Bruno", planning.bruno["email"])
    assert response.status_code == 201
    assert response.json()["user_id"] == planning.bruno["id"]


@ENDINGS
def test_r28_upcoming_registrations_become_cancelled(
    client: Any, new_client: Callable[[], Any], end: Callable[[Planning], None]
) -> None:
    planning = Planning(client, new_client)
    planning.add_slot("thursday", *THURSDAY)
    planning.add_slot("saturday", *THURSDAY)
    confirmed_day = day_of_week("thursday")
    proposed_day = day_of_week("saturday", 3)
    planning.registered(planning.bruno_client, planning.bruno, confirmed_day, *THURSDAY)
    planning.registered(planning.alice_client, planning.bruno, proposed_day, *THURSDAY)

    end(planning)

    for day in (confirmed_day, proposed_day):
        registration = registration_on(planning, day)
        assert registration is not None
        assert registration["user_id"] == planning.bruno["id"]
        assert registration["display_name"] == "Bruno"
        assert registration["status"] == "cancelled"


def test_r28_the_freed_occurrence_can_be_registered_again(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    planning.add_slot("thursday", *THURSDAY)
    day = day_of_week("thursday")
    planning.registered(planning.bruno_client, planning.bruno, day, *THURSDAY)

    remove(planning, planning.bruno)

    response = planning.register(planning.chloe_client, planning.chloe, day, *THURSDAY)
    assert response.status_code == 201


@ENDINGS
def test_r28_past_registrations_stay_with_the_display_name(
    client: Any, new_client: Callable[[], Any], end: Callable[[Planning], None]
) -> None:
    planning = Planning(client, new_client)
    planning.add_slot("thursday", *THURSDAY)
    registration = planning.registered(
        planning.bruno_client, planning.bruno, day_of_week("thursday"), *THURSDAY
    )
    past_day = move_a_year_back(registration)

    end(planning)

    assert registration_on(planning, past_day) == {
        "id": registration["id"],
        "user_id": planning.bruno["id"],
        "display_name": "Bruno",
        "status": "confirmed",
    }


def test_r28_registrations_of_other_members_and_associations_stay(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    planning.add_slot("thursday", *THURSDAY)
    chloe_day = day_of_week("thursday")
    chloes = planning.registered(planning.chloe_client, planning.chloe, chloe_day, *THURSDAY)
    other = Planning(new_client(), new_client)
    other.add_slot("thursday", *THURSDAY)
    joined = add_member(other.alice_client, other.id, "Bruno", planning.bruno["email"])
    assert joined.status_code == 201
    other.registered(other.alice_client, planning.bruno, chloe_day, *THURSDAY)

    remove(planning, planning.bruno)

    assert registration_on(planning, chloe_day) == {
        "id": chloes["id"],
        "user_id": planning.chloe["id"],
        "display_name": "Chloé",
        "status": "confirmed",
    }
    in_other = registration_on(other, chloe_day)
    assert in_other is not None
    assert in_other["user_id"] == planning.bruno["id"]
    assert in_other["status"] == "proposed"


def chosen(planning: Planning, as_client: Any, slot: dict[str, Any], value: str) -> None:
    """Chooses `value` for `slot` in the user's own My preferences."""
    text = shown(set_my_preference(as_client, planning.slug, slot["id"], value))
    assert "Something went wrong" not in text, text


def test_r28_preferences_absences_and_note_are_deleted(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    slot = planning.add_slot("thursday", *THURSDAY)
    bruno = planning.bruno_client
    chosen(planning, bruno, slot, "preferred")
    absence = {"first": "2037-11-09", "last": "2037-11-15"}
    assert bruno.post(planning.path("absences"), json=absence).status_code == 201
    assert bruno.put(planning.path("note"), json={"text": "Pairs, please."}).status_code == 200

    remove(planning, planning.bruno)

    manager = planning.alice_client
    assert preferences_stored(manager, planning.slug) == set()
    assert manager.get(planning.path("member-absences")).json() == []
    rejoin(planning)
    assert preferences_stored(manager, planning.slug) == set()
    assert availability_lines(bruno, planning.slug, "Absences") == []
    note = availability_section(bruno, planning.slug, "Note for the managers")
    assert note == "Note for the managers None"


def test_r28_account_deletion_deletes_preferences_absences_and_note(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    slot = planning.add_slot("thursday", *THURSDAY)
    bruno = planning.bruno_client
    chosen(planning, bruno, slot, "preferred")
    absence = {"first": "2026-11-09", "last": "2026-11-15"}
    assert bruno.post(planning.path("absences"), json=absence).status_code == 201
    assert bruno.put(planning.path("note"), json={"text": "Pairs, please."}).status_code == 200
    assert preferences_held(planning.bruno) == 1

    delete_account(bruno)

    manager = planning.alice_client
    assert preferences_held(planning.bruno) == 0
    assert preferences_stored(manager, planning.slug) == set()
    assert manager.get(planning.path("member-absences")).json() == []
    notes = manager.get(planning.path("notes")).json()
    assert planning.bruno["id"] not in [n["user_id"] for n in notes]


def test_r28_preferences_of_the_other_members_stay(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    slot = planning.add_slot("thursday", *THURSDAY)
    chosen(planning, planning.chloe_client, slot, "possible")

    remove(planning, planning.bruno)

    assert preferences_stored(planning.alice_client, planning.slug) == {
        ("Chloé", "Thu 10:00–13:00", "possible")  # noqa: RUF001
    }
