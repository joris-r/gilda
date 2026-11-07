import html
import re
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


def part(page: str, tag: str) -> str:
    match = re.search(rf"<{tag}[ >].*</{tag}>", page, re.DOTALL)
    assert match, f"no {tag} in {page}"
    return match.group(0)


def text_of(fragment: str) -> str:
    """What a piece of HTML shows, without its tags and attributes."""
    return html.unescape(re.sub(r"<[^>]+>", " ", fragment))


def without_dialogs(fragment: str) -> str:
    return re.sub(r"<dialog.*?</dialog>", "", fragment, flags=re.DOTALL)


def lines_of(fragment: str) -> list[str]:
    """The text of each list item outside the dialogs, in order, its spaces collapsed."""
    items = re.findall(r"<li.*?</li>", without_dialogs(fragment), re.DOTALL)
    return [" ".join(text_of(item).split()) for item in items]


def without_hidden(fragment: str) -> str:
    """The HTML without its hidden paragraphs, such as the errors and notice not shown yet."""
    return re.sub(
        r'<p(?=[^>]*(\shidden[\s>]|style="display: none"))[^>]*>.*?</p>',
        "",
        fragment,
        flags=re.DOTALL,
    )


def section_of(page: str, heading: str) -> str:
    """What main shows, outside the dialogs, from the `heading` title to the next one."""
    main = without_hidden(without_dialogs(part(page, "main")))
    for chunk in re.split(r"(?=<h2[ >])", main):
        if re.match(rf"<h2[^>]*>\s*{re.escape(heading)}\s*</h2>", chunk):
            return chunk
    raise AssertionError(f"no section {heading} in {main}")


def settings_page(as_client: Any, slug: str) -> str:
    response = as_client.get(f"/association/{slug}/settings")
    assert response.status_code == 200
    return str(response.text)


def settings_section(as_client: Any, slug: str, heading: str) -> str:
    """The text that the `heading` section of Schedule settings shows, its spaces collapsed."""
    return " ".join(text_of(section_of(settings_page(as_client, slug), heading)).split())


def settings_lines(as_client: Any, slug: str, heading: str) -> list[str]:
    """The lines that the `heading` section of Schedule settings lists."""
    return lines_of(section_of(settings_page(as_client, slug), heading))


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

    def edit_closure(
        self, closure: dict[str, Any], first: str, last: str, label: str | None = None
    ) -> None:
        """Alice saves the dialog "Edit the closure" of `closure` on Schedule settings."""
        response = edit_closure(self.alice_client, self.slug, closure["id"], first, last, label)
        assert GENERIC not in shown(response)

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


def set_period(as_client: Any, slug: str, first: str, last: str) -> Any:
    """Submits the dialog "Planning period" on Schedule settings."""
    return as_client.post(
        f"/association/{slug}/settings/period", json={"first": first, "last": last}
    )


def clear_period(as_client: Any, slug: str) -> Any:
    """Confirms "Clear the planning period?" on Schedule settings."""
    return as_client.post(f"/association/{slug}/settings/period/clear", json={})


def add_closure_on_screen(
    as_client: Any, slug: str, first: str, last: str, label: str | None = ""
) -> Any:
    """Submits the dialog "Add a closure" on Schedule settings."""
    return as_client.post(
        f"/association/{slug}/settings/closures",
        json={"first": first, "last": last, "label": label},
    )


def edit_closure(
    as_client: Any, slug: str, closure_id: str, first: str, last: str, label: str | None = ""
) -> Any:
    """Submits the dialog "Edit the closure" of a closure on Schedule settings."""
    return as_client.post(
        f"/association/{slug}/settings/closures/{closure_id}/edit",
        json={"first": first, "last": last, "label": label},
    )


def delete_closure(as_client: Any, slug: str, closure_id: str) -> Any:
    """Confirms "Delete the closure" of a closure on Schedule settings."""
    return as_client.post(f"/association/{slug}/settings/closures/{closure_id}/delete", json={})


def availability_page(as_client: Any, slug: str) -> str:
    response = as_client.get(f"/association/{slug}/availability")
    assert response.status_code == 200
    return str(response.text)


def set_my_preference(as_client: Any, slug: str, slot_id: str, value: str) -> Any:
    """Chooses `value` in the selector of a slot on My availability; "" stands for "—"."""
    return as_client.post(
        f"/association/{slug}/availability/preferences/{slot_id}", json={"value": value}
    )


def availability_section(as_client: Any, slug: str, heading: str) -> str:
    """The text that the `heading` section of My availability shows, its spaces collapsed."""
    return " ".join(text_of(section_of(availability_page(as_client, slug), heading)).split())


def availability_lines(as_client: Any, slug: str, heading: str) -> list[str]:
    """The lines that the `heading` section of My availability lists."""
    return lines_of(section_of(availability_page(as_client, slug), heading))


def add_absence(as_client: Any, planning: Planning, first: str, last: str) -> dict[str, Any]:
    """Adds an absence of the user's own through the API."""
    response = as_client.post(planning.path("absences"), json={"first": first, "last": last})
    assert response.status_code == 201, response.text
    absence: dict[str, Any] = response.json()
    return absence


def write_note(as_client: Any, planning: Planning, text: str) -> None:
    """Sets the user's own note through the API."""
    response = as_client.put(planning.path("note"), json={"text": text})
    assert response.status_code == 200, response.text


def add_absence_on_screen(as_client: Any, slug: str, first: str, last: str) -> Any:
    """Submits the dialog "Add an absence" on My availability."""
    return as_client.post(
        f"/association/{slug}/availability/absences", json={"first": first, "last": last}
    )


def edit_absence(as_client: Any, slug: str, absence_id: str, first: str, last: str) -> Any:
    """Submits the dialog "Edit the absence" of an absence on My availability."""
    return as_client.post(
        f"/association/{slug}/availability/absences/{absence_id}/edit",
        json={"first": first, "last": last},
    )


def delete_absence(as_client: Any, slug: str, absence_id: str) -> Any:
    """Confirms "Delete the absence" of an absence on My availability."""
    return as_client.post(f"/association/{slug}/availability/absences/{absence_id}/delete", json={})


def save_note(as_client: Any, slug: str, text: str) -> Any:
    """Submits the dialog "Note for the managers" on My availability."""
    return as_client.post(f"/association/{slug}/availability/note", json={"text": text})
