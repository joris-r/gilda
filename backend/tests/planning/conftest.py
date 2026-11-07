from collections.abc import Callable
from datetime import date, timedelta
from typing import Any

from tests.core.conftest import (  # noqa: F401  (fixtures used by the planning tests)
    add_member,
    client,
    create_association,
    new_client,
    shown,
    sign_up,
    unique_email,
)

GENERIC = "Something went wrong. Try again."

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def day_of_week(weekday: str, weeks_ahead: int = 1) -> str:
    """The date of `weekday` in the week `weeks_ahead` weeks after the current one."""
    today = date.today()
    monday = today - timedelta(days=today.weekday()) + timedelta(weeks=weeks_ahead)
    return (monday + timedelta(days=WEEKDAYS.index(weekday))).isoformat()


class Planning:
    """Alice manages an association; Bruno and Chloé volunteer in it, each on their own client."""

    def __init__(self, alice_client: Any, open_client: Callable[[], Any]) -> None:
        self.alice_client = alice_client
        self.alice = sign_up(alice_client, "Alice")
        self.association = create_association(alice_client)
        self.id = self.association["id"]
        self.slug = self.association["slug"]
        self.slots: list[dict[str, Any]] = []
        self.bruno_client, self.bruno = self._volunteer(open_client, "Bruno")
        self.chloe_client, self.chloe = self._volunteer(open_client, "Chloé")

    def _volunteer(self, open_client: Callable[[], Any], name: str) -> tuple[Any, dict[str, Any]]:
        volunteer_client = open_client()
        email = unique_email(name.replace("é", "e"))
        user = sign_up(volunteer_client, name, email)
        assert add_member(self.alice_client, self.id, name, email).status_code == 201
        return volunteer_client, user

    def path(self, rest: str) -> str:
        return f"/api/associations/{self.id}/{rest}"

    def add_slot(self, weekday: str, start: str, end: str) -> dict[str, Any]:
        response = self.alice_client.post(
            self.path("slots"), json={"weekday": weekday, "start": start, "end": end}
        )
        assert response.status_code == 201, response.text
        slot: dict[str, Any] = response.json()
        self.slots.append(slot)
        return slot

    def edit_slot(self, slot: dict[str, Any], weekday: str, start: str, end: str) -> None:
        """Alice saves the dialog "Edit the slot" of `slot` on Schedule settings."""
        text = shown(edit_slot(self.alice_client, self.slug, slot["id"], weekday, start, end))
        assert GENERIC not in text, text

    def delete_slot(self, slot: dict[str, Any]) -> None:
        """Alice confirms "Delete the slot" of `slot` on Schedule settings."""
        text = shown(delete_slot(self.alice_client, self.slug, slot["id"]))
        assert GENERIC not in text, text

    def add_closure(self, first: str, last: str, label: str | None = None) -> dict[str, Any]:
        response = self.alice_client.post(
            self.path("closures"), json={"first": first, "last": last, "label": label}
        )
        assert response.status_code == 201, response.text
        closure: dict[str, Any] = response.json()
        return closure

    def register(self, as_client: Any, user: dict[str, Any], day: str, start: str, end: str) -> Any:
        return as_client.post(
            self.path("registrations"),
            json={"user_id": user["id"], "date": day, "start": start, "end": end},
        )

    def registered(
        self, as_client: Any, user: dict[str, Any], day: str, start: str, end: str
    ) -> dict[str, Any]:
        response = self.register(as_client, user, day, start, end)
        assert response.status_code == 201, response.text
        registration: dict[str, Any] = response.json()
        return registration

    def set_status(self, as_client: Any, registration: dict[str, Any], status: str) -> Any:
        return as_client.patch(
            self.path(f"registrations/{registration['id']}"), json={"status": status}
        )

    def schedule(self, as_client: Any, first: str, last: str) -> dict[str, Any]:
        response = as_client.get(self.path("schedule"), params={"from": first, "to": last})
        assert response.status_code == 200, response.text
        body: dict[str, Any] = response.json()
        return body


def add_slot_on_screen(as_client: Any, slug: str, weekday: str, start: str, end: str) -> Any:
    """Submits the dialog "Add a slot" on Schedule settings."""
    return as_client.post(
        f"/association/{slug}/settings/slots",
        json={"weekday": weekday, "start": start, "end": end},
    )


def edit_slot(as_client: Any, slug: str, slot_id: str, weekday: str, start: str, end: str) -> Any:
    """Submits the dialog "Edit the slot" of a slot on Schedule settings."""
    return as_client.post(
        f"/association/{slug}/settings/slots/{slot_id}/edit",
        json={"weekday": weekday, "start": start, "end": end},
    )


def delete_slot(as_client: Any, slug: str, slot_id: str) -> Any:
    """Confirms "Delete the slot" of a slot on Schedule settings."""
    return as_client.post(f"/association/{slug}/settings/slots/{slot_id}/delete", json={})
