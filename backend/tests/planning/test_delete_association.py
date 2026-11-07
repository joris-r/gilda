import asyncio
import os
from collections.abc import Callable
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from tests.core.conftest import delete_association, shown
from tests.planning.conftest import (
    Planning,
    add_member,
    create_association,
    day_of_week,
    set_my_preference,
)

THURSDAY = ("10:00", "13:00")
HELD_BY_ASSOCIATION = (
    "membership",
    "slot",
    "closure",
    "planning_period",
    "registration",
    "absence",
    "note",
    "share_link",
)


def rows_held(association_id: str, slot_id: str) -> dict[str, int]:
    """Counts the stored rows of an association, which the API can no longer show once deleted."""

    async def run() -> dict[str, int]:
        engine = create_async_engine(os.environ["DATABASE_URL"])
        counts: dict[str, int] = {}
        async with engine.begin() as connection:
            for table in HELD_BY_ASSOCIATION:
                result = await connection.execute(
                    text(f"SELECT count(*) FROM {table} WHERE association_id = :id"),
                    {"id": association_id},
                )
                counts[table] = result.scalar_one()
            result = await connection.execute(
                text("SELECT count(*) FROM preference WHERE slot_id = :id"), {"id": slot_id}
            )
            counts["preference"] = result.scalar_one()
        await engine.dispose()
        return counts

    return asyncio.run(run())


def deleted(planning: Planning) -> None:
    """Alice confirms "Delete the association" on Members, which leads to My associations."""
    text = shown(delete_association(planning.alice_client, planning.association["slug"]))
    assert "window.location" in text, text


def filled(planning: Planning) -> tuple[dict[str, Any], str, str]:
    """Gives the association one of everything; returns its slot, share token and a Thursday."""
    alice, bruno = planning.alice_client, planning.bruno_client
    slot = planning.add_slot("thursday", *THURSDAY)
    planning.add_closure(day_of_week("saturday"), day_of_week("saturday"), "Fête du quartier")
    day = day_of_week("thursday")
    period = alice.put(planning.path("planning-period"), json={"first": day, "last": day})
    assert period.status_code == 200, period.text
    planning.registered(bruno, planning.bruno, day, *THURSDAY)
    preference = shown(set_my_preference(bruno, planning.slug, slot["id"], "possible"))
    assert "Something went wrong" not in preference, preference
    absence = bruno.post(planning.path("absences"), json={"first": day, "last": day})
    assert absence.status_code == 201, absence.text
    note = bruno.put(planning.path("note"), json={"text": "Mornings only."})
    assert note.status_code == 200, note.text
    share_link = alice.post(planning.path("share-link"))
    assert share_link.status_code == 201, share_link.text
    return slot, share_link.json()["token"], day


def test_r34_everything_the_association_holds_is_erased(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    slot, _, _ = filled(planning)
    assert all(rows_held(planning.id, slot["id"]).values())

    deleted(planning)

    assert not any(rows_held(planning.id, slot["id"]).values())


@pytest.mark.parametrize("path", ["", "/schedule"])
def test_r34_the_share_link_no_longer_shows_the_schedule(
    client: Any, new_client: Callable[[], Any], path: str
) -> None:
    planning = Planning(client, new_client)
    _, token, _ = filled(planning)

    deleted(planning)

    assert new_client().get(f"/api/shared/{token}{path}").status_code == 404


@pytest.mark.parametrize("rest", ["member-absences", "notes", "share-link"])
def test_r34_its_planning_endpoints_answer_404(
    client: Any, new_client: Callable[[], Any], rest: str
) -> None:
    planning = Planning(client, new_client)
    filled(planning)

    deleted(planning)

    assert client.get(planning.path(rest)).status_code == 404


def test_r34_another_association_of_its_members_keeps_what_it_holds(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    filled(planning)
    day = day_of_week("thursday")
    other = create_association(client, "Repair Café Belleville")
    at = f"/api/associations/{other['id']}"
    assert add_member(client, other["id"], "Bruno", planning.bruno["email"]).status_code == 201
    slot = client.post(
        f"{at}/slots", json={"weekday": "thursday", "start": "10:00", "end": "13:00"}
    )
    assert slot.status_code == 201, slot.text
    registration = planning.bruno_client.post(
        f"{at}/registrations",
        json={"user_id": planning.bruno["id"], "date": day, "start": "10:00", "end": "13:00"},
    )
    assert registration.status_code == 201, registration.text

    deleted(planning)

    associations = planning.bruno_client.get("/api/associations").json()
    assert [a["id"] for a in associations] == [other["id"]]
    assert [r["id"] for r in associations[0]["upcoming"]] == [registration.json()["id"]]
    assert all(rows_held(other["id"], slot.json()["id"])[t] for t in ("membership", "slot"))
