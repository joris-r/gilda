import asyncio
import os
from collections.abc import Callable
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from tests.core.conftest import delete_association, my_associations_listed, shown
from tests.planning.conftest import (
    GENERIC,
    Planning,
    add_absence,
    add_member,
    add_slot,
    create_association,
    day_of_week,
    set_my_preference,
    shared_page,
    shared_token,
    sign_up_for,
    write_note,
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
    """Counts the stored rows of an association, which no screen shows once deleted."""

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
    bruno = planning.bruno_client
    slot = planning.add_slot("thursday", *THURSDAY)
    planning.add_closure(day_of_week("saturday"), day_of_week("saturday"), "Fête du quartier")
    day = day_of_week("thursday")
    planning.set_period(day, day)
    planning.registered(bruno, planning.bruno, day, *THURSDAY)
    preference = shown(set_my_preference(bruno, planning.slug, slot["id"], "possible"))
    assert "Something went wrong" not in preference, preference
    add_absence(bruno, planning, day, day)
    write_note(bruno, planning, "Mornings only.")
    return slot, shared_token(planning), day


# /planning/operations/delete-association/planning
# /core/operations/delete-association/deleted
def test_everything_the_association_holds_is_erased(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    slot, _, _ = filled(planning)
    assert all(rows_held(planning.id, slot["id"]).values())

    deleted(planning)

    assert not any(rows_held(planning.id, slot["id"]).values())


# /planning/ui/shared-schedule/invalid
# /planning/operations/delete-association/planning
def test_the_share_link_no_longer_shows_the_schedule(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    _, token, _ = filled(planning)

    deleted(planning)

    response = shared_page(new_client(), token)
    assert response.status_code == 200
    assert "This link is no longer valid." in response.text
    assert "Week" not in response.text


# /core/operations/delete-association/silent
def test_another_association_of_its_members_keeps_what_it_holds(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    filled(planning)
    day = day_of_week("thursday")
    other = create_association(client, "Repair Café Belleville")
    add_member(client, other["slug"], "Bruno", planning.bruno["email"])
    slot = add_slot(client, other, "thursday", "10:00", "13:00")
    weeks = {"from": day, "to": day}
    text = shown(sign_up_for(planning.bruno_client, other["slug"], day, "10:00", "13:00", weeks))
    assert GENERIC not in text, text

    deleted(planning)

    associations = my_associations_listed(planning.bruno_client)
    assert [a.name for a in associations] == [other["name"]]
    assert len(associations[0].lines) == 1
    assert all(rows_held(other["id"], slot["id"])[t] for t in ("membership", "slot"))
