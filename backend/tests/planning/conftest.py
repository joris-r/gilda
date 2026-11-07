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

    def cancel(self, as_client: Any, registration: dict[str, Any]) -> None:
        """Confirms "Cancel registration…" in the menu of `registration` on the Schedule."""
        text = shown(cancel_registration(as_client, self.slug, registration["id"]))
        assert GENERIC not in text, text


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


def set_member_preference(as_client: Any, slug: str, slot_id: str, user_id: str, value: str) -> Any:
    """Chooses `value` in the selector of a member and slot in Members' preferences on Schedule
    settings; "" stands for "—"."""
    return as_client.post(
        f"/association/{slug}/settings/preferences/{slot_id}/{user_id}", json={"value": value}
    )


def selected_option(select: str) -> tuple[str, str]:
    """The value and label of the option a selector shows chosen, or of its first one."""
    options = re.findall(r'<option[^>]*?value="([^"]*)"([^>]*)>(.*?)</option>', select, re.DOTALL)
    assert options, select
    chosen = [(value, label) for value, attributes, label in options if " selected" in attributes]
    assert len(chosen) <= 1, select
    value, label = chosen[0] if chosen else (options[0][0], options[0][2])
    return value, " ".join(text_of(label).split())


def preferences_grid(as_client: Any, slug: str) -> tuple[list[str], list[tuple[str, list[str]]]]:
    """Members' preferences on Schedule settings: the slot of each column, and each row's member
    with the label that each of its selectors shows."""
    section = section_of(settings_page(as_client, slug), "Members' preferences")
    rows = re.findall(r"<tr.*?</tr>", section, re.DOTALL)
    assert rows, section
    head = re.findall(r"<th.*?</th>", rows[0], re.DOTALL)
    columns = [" ".join(text_of(cell).split()) for cell in head[1:]]
    members = []
    for row in rows[1:]:
        selects = re.findall(r"<select.*?</select>", row, re.DOTALL)
        assert len(selects) == len(columns), row
        name = " ".join(text_of(re.sub(r"<select.*?</select>", "", row, flags=re.DOTALL)).split())
        members.append((name, [selected_option(select)[1] for select in selects]))
    return columns, members


def preferences_stored(as_client: Any, slug: str) -> set[tuple[str, str, str]]:
    """The preferences of the association, as a manager's Members' preferences shows them: each
    member's name, the slot's column and the value of each selector not on "—"."""
    section = section_of(settings_page(as_client, slug), "Members' preferences")
    rows = re.findall(r"<tr.*?</tr>", section, re.DOTALL)
    if not rows:
        return set()
    head = re.findall(r"<th.*?</th>", rows[0], re.DOTALL)
    columns = [" ".join(text_of(cell).split()) for cell in head[1:]]
    stored = set()
    for row in rows[1:]:
        selects = re.findall(r"<select.*?</select>", row, re.DOTALL)
        name = " ".join(text_of(re.sub(r"<select.*?</select>", "", row, flags=re.DOTALL)).split())
        for column, select in zip(columns, selects, strict=True):
            value = selected_option(select)[0]
            if value:
                stored.add((name, column, value))
    return stored


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


MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def day_label(day: str) -> str:
    """How the Schedule heads the column of a date, e.g. "Thu 29 Oct"."""
    value = date.fromisoformat(day)
    return f"{WEEKDAYS[value.weekday()][:3].title()} {value.day} {MONTHS[value.month - 1]}"


def schedule_page(as_client: Any, slug: str) -> str:
    response = as_client.get(f"/association/{slug}")
    assert response.status_code == 200
    return str(response.text)


def _occurrence_text(item: str) -> str:
    """What an occurrence or an obsolete registration shows, between brackets, a struck name
    between ~~."""
    struck = re.sub(r"<s[ >](.*?)</s>", lambda m: f"~~{text_of(m.group(1)).strip()}~~", item)
    return "[" + " ".join(text_of(struck).split()) + "]"


Week = tuple[str, list[str]]


def schedule_entries(fragment: str) -> list[str | Week]:
    """The lines and weeks a piece of the Schedule shows, in order: a line as its text; a week as
    its heading and the text of each of its days, e.g. ("Week 44", ["Thu 29 Oct [Chloé]",
    "Sat 31 Oct [~~Bruno~~]"]). A day is an element with role="group"; it shows its label, then
    a closure's "Closed" and label, then each occurrence or obsolete registration, an `<li>`,
    between brackets. A line is a `<p class="line">`, a week a `<section class="week">`."""
    fragment = re.sub(r"^data: elements ", "", fragment, flags=re.MULTILINE)
    entries: list[str | Week] = []
    pattern = (
        r'<p[^>]*class="line[^"]*"[^>]*>.*?</p>'
        r'|<section[^>]*class="week[^"]*"[^>]*>.*?</section>'
    )
    for match in re.finditer(pattern, fragment, re.DOTALL):
        found = match.group(0)
        if found.startswith("<p"):
            entries.append(" ".join(text_of(found).split()))
            continue
        heading = re.search(r"<h2[^>]*>(.*?)</h2>", found, re.DOTALL)
        assert heading, found
        days = []
        for chunk in re.split(r'(?=<[a-z]+[^>]*\srole="group")', found)[1:]:
            items = re.sub(
                r"<li[ >].*?</li>",
                lambda m: f" {_occurrence_text(m.group(0))} ",
                chunk,
                flags=re.DOTALL,
            )
            days.append(" ".join(text_of(items).split()))
        entries.append((" ".join(text_of(heading.group(1)).split()), days))
    return entries


def schedule_shown(as_client: Any, slug: str) -> list[str | Week]:
    """The lines and weeks the Schedule shows, as schedule_entries reads them."""
    return schedule_entries(without_dialogs(part(schedule_page(as_client, slug), "main")))


def headings_of(entries: list[str | Week]) -> list[str]:
    """The heading of each week, in order."""
    return [entry[0] for entry in entries if isinstance(entry, tuple)]


def day_in(entries: list[str | Week], day: str) -> str:
    """What the Schedule shows on `day`, after its label, e.g. "[Bruno ?]" or "Closed Fête"."""
    label = day_label(day)
    found = [
        text
        for entry in entries
        if isinstance(entry, tuple)
        for text in entry[1]
        if text == label or text.startswith(f"{label} ")
    ]
    assert len(found) == 1, (label, entries)
    return found[0].removeprefix(label).strip()


def day_shown(as_client: Any, slug: str, day: str) -> str:
    """What the Schedule shows on `day`, after its label."""
    return day_in(schedule_shown(as_client, slug), day)


def opened_weeks() -> dict[str, str]:
    """The weeks the Schedule opens on without a planning period (R32), as its actions get
    them."""
    return {"from": day_of_week("monday", -1), "to": day_of_week("sunday", 4)}


def open_menu(as_client: Any, slug: str, day: str, start: str, end: str) -> Any:
    """Clicks the occurrence, or the obsolete registration, of `day` from `start` to `end` on
    the Schedule."""
    return as_client.post(
        f"/association/{slug}/menu", json={"date": day, "start": start, "end": end}
    )


def sign_up_for(
    as_client: Any,
    slug: str,
    day: str,
    start: str,
    end: str,
    weeks: dict[str, str] | None = None,
) -> Any:
    """Clicks "Sign up" in the menu of an occurrence, on a Schedule that shows `weeks`."""
    return as_client.post(
        f"/association/{slug}/sign-up",
        json={"date": day, "start": start, "end": end, **(weeks or opened_weeks())},
    )


def propose(
    as_client: Any,
    slug: str,
    user_id: str,
    day: str,
    start: str,
    end: str,
    weeks: dict[str, str] | None = None,
) -> Any:
    """Clicks the display name of the member `user_id` in the menu of an occurrence, on a
    Schedule that shows `weeks`."""
    return as_client.post(
        f"/association/{slug}/propose",
        json={
            "user_id": user_id,
            "date": day,
            "start": start,
            "end": end,
            **(weeks or opened_weeks()),
        },
    )


Name = tuple[str, list[str]]


def menu_names(fragment: str) -> list[Name]:
    """The members' names a menu offers, in order: each one's text, its count included, e.g.
    "Alice (2)", and the text of each of its icons, e.g. ["Absent Mon 9 Nov 2026"]. A name is
    an `<li>` of the menu; an icon, an element in it with an aria-label, whose text that is."""
    fragment = re.sub(r"^data: elements ", "", fragment, flags=re.MULTILINE)
    names: list[Name] = []
    for item in re.findall(r"<li[ >].*?</li>", without_dialogs(fragment), re.DOTALL):
        icons = re.findall(r'<[a-z]+[^>]*\saria-label="([^"]*)"', item)
        labelled = r'<([a-z]+)[^>]*\saria-label="[^"]*"[^>]*>.*?</\1>'
        text = re.sub(labelled, "", item, flags=re.DOTALL)
        names.append((" ".join(text_of(text).split()), [html.unescape(icon) for icon in icons]))
    return names


def names_offered(
    as_client: Any, slug: str, day: str, start: str = "10:00", end: str = "13:00"
) -> list[Name]:
    """The members' names the menu of the occurrence of `day` offers, as menu_names reads
    them."""
    response = open_menu(as_client, slug, day, start, end)
    assert response.status_code == 200
    return menu_names(shown(response))


def notes_offered(planning: Planning) -> dict[str, str]:
    """The note of Alice, Bruno and Chloé, by user id, as the note icons of Alice's menu show
    them on a free Thursday two weeks ahead, "" for a name with no icon; adds a Thursday slot
    when the planning has none. The members hold no absence then."""
    if not any(slot["weekday"] == "thursday" for slot in planning.slots):
        planning.add_slot("thursday", "10:00", "13:00")
        start, end = "10:00", "13:00"
    else:
        slot = next(slot for slot in planning.slots if slot["weekday"] == "thursday")
        start, end = slot["start"], slot["end"]
    day = day_of_week("thursday", 2)
    names = names_offered(planning.alice_client, planning.slug, day, start, end)
    users = {u["display_name"]: u["id"] for u in (planning.alice, planning.bruno, planning.chloe)}
    notes = {}
    for text, icons in names:
        assert len(icons) <= 1, names
        notes[users[re.sub(r" \(\d+\)$", "", text)]] = icons[0] if icons else ""
    return notes


def confirm_registration(
    as_client: Any, slug: str, registration_id: str, weeks: dict[str, str] | None = None
) -> Any:
    """Clicks "Confirm" in the menu of a registration, on a Schedule that shows `weeks`."""
    return as_client.post(
        f"/association/{slug}/registrations/{registration_id}/confirm",
        json=weeks or opened_weeks(),
    )


def cancel_registration(
    as_client: Any, slug: str, registration_id: str, weeks: dict[str, str] | None = None
) -> Any:
    """Confirms "Cancel registration…" in the menu of a registration, on a Schedule that shows
    `weeks`."""
    return as_client.post(
        f"/association/{slug}/registrations/{registration_id}/cancel",
        json=weeks or opened_weeks(),
    )


def more_weeks(as_client: Any, slug: str, first: str, last: str) -> Any:
    """Clicks "More weeks" on a Schedule that shows the weeks from `first` to `last`."""
    return as_client.post(f"/association/{slug}/weeks", json={"from": first, "to": last})
