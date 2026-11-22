import re
from collections.abc import Callable
from datetime import date, timedelta
from typing import Any

from tests.conftest import clock
from tests.core.conftest import (  # noqa: F401  (fixtures used by the planning tests)
    add_member,
    client,
    create_association,
    new_client,
    patched,
    run_sql,
    run_sql_rows,
    shown,
    sign_up,
    unique_email,
)
from tests.page import (
    Element,
    lines_of,
    parse,
    part,
    text_of,
)

GENERIC = "Something went wrong. Try again."
TAKEN = "Someone took this slot in the meantime."

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def day_of_week(weekday: str, weeks_ahead: int = 1) -> str:
    """The date of `weekday` in the week `weeks_ahead` weeks after the current one."""
    today = clock.today("UTC")
    monday = today - timedelta(days=today.weekday()) + timedelta(weeks=weeks_ahead)
    return (monday + timedelta(days=WEEKDAYS.index(weekday))).isoformat()


def section_of(page: str, heading: str) -> str:
    """The HTML of the section that main shows under the `heading` title, with only what it
    shows."""
    main = parse(page).first("main")
    titles = [title for title in main.elements("h2") if title.text == heading]
    assert len(titles) == 1, f"no section {heading} in {main.html}"
    section = titles[0].parent
    while section is not None and section.tag != "section":
        section = section.parent
    assert section is not None, f"{heading} heads no section"
    return section.html


def settings_page(as_client: Any, slug: str) -> str:
    response = as_client.get(f"/association/{slug}/settings")
    assert response.status_code == 200
    return str(response.text)


def settings_section(as_client: Any, slug: str, heading: str) -> str:
    """The text that the `heading` section of Schedule settings shows, its spaces collapsed."""
    return text_of(section_of(settings_page(as_client, slug), heading))


def settings_lines(as_client: Any, slug: str, heading: str) -> list[str]:
    """The lines that the `heading` section of Schedule settings lists."""
    return lines_of(section_of(settings_page(as_client, slug), heading))


def added_id(table: str, association_id: str, action: Callable[[], Any]) -> str:
    """Runs `action`, which adds one row to `table` in the association, and returns its id,
    read from the database: the screens show no ids."""
    sql = f"SELECT id FROM {table} WHERE association_id = :association"
    before = {row[0] for row in run_sql_rows(sql, association=association_id)}
    action()
    added = {row[0] for row in run_sql_rows(sql, association=association_id)} - before
    assert len(added) == 1, added
    return str(added.pop())


def add_slot(
    as_client: Any, association: dict[str, Any], weekday: str, start: str, end: str
) -> dict[str, Any]:
    """Adds a slot with "Add a slot" on Schedule settings."""

    def add() -> None:
        text = shown(add_slot_on_screen(as_client, association["slug"], weekday, start, end))
        assert GENERIC not in text, text

    slot_id = added_id("slot", association["id"], add)
    return {"id": slot_id, "weekday": weekday, "start": start, "end": end}


def add_closure(
    as_client: Any, association: dict[str, Any], first: str, last: str, label: str | None = None
) -> dict[str, Any]:
    """Adds a closure with "Add a closure" on Schedule settings."""

    def add() -> None:
        text = shown(add_closure_on_screen(as_client, association["slug"], first, last, label))
        assert GENERIC not in text, text

    closure_id = added_id("closure", association["id"], add)
    return {"id": closure_id, "first": first, "last": last, "label": label}


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
        add_member(self.alice_client, self.slug, name, email)
        return volunteer_client, user

    def add_slot(self, weekday: str, start: str, end: str) -> dict[str, Any]:
        """Alice adds a slot with "Add a slot" on Schedule settings."""
        slot = add_slot(self.alice_client, self.association, weekday, start, end)
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
        """Alice adds a closure with "Add a closure" on Schedule settings."""
        return add_closure(self.alice_client, self.association, first, last, label)

    def edit_closure(
        self, closure: dict[str, Any], first: str, last: str, label: str | None = None
    ) -> None:
        """Alice saves the dialog "Edit the closure" of `closure` on Schedule settings."""
        response = edit_closure(self.alice_client, self.slug, closure["id"], first, last, label)
        assert GENERIC not in shown(response)

    def set_period(self, first: str, last: str) -> None:
        """Alice saves the dialog "Planning period" on Schedule settings."""
        text = shown(set_period(self.alice_client, self.slug, first, last))
        assert GENERIC not in text, text

    def registered(
        self, as_client: Any, user: dict[str, Any], day: str, start: str, end: str
    ) -> dict[str, Any]:
        """Registers `user` on the occurrence by their display name in its menu on the Schedule,
        signed in on `as_client`: confirmed for the user signed in there, proposed by a manager
        otherwise."""
        weeks = {"from": day, "to": day}

        def register() -> None:
            text = shown(propose(as_client, self.slug, user["id"], day, start, end, weeks))
            assert GENERIC not in text, text
            assert TAKEN not in text, text

        registration_id = added_id("registration", self.id, register)
        return {"id": registration_id, "user_id": user["id"], "date": day, "start": start}

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


def _selected(select: Element) -> tuple[str, str]:
    options = list(select.elements("option"))
    assert options, select
    chosen = [option for option in options if option.has("selected")]
    assert len(chosen) <= 1, select
    option = chosen[0] if chosen else options[0]
    return option.get("value") or "", option.text


def selected_option(select: str) -> tuple[str, str]:
    """The value and label of the option a selector shows chosen, or of its first one."""
    return _selected(parse(select).first("select"))


def _preference_rows(section: str) -> tuple[list[str], list[tuple[str, list[Element]]]]:
    """The slot of each column of a grid of preferences, and each row's member with its
    selectors."""
    rows = list(parse(section).elements("tr"))
    if not rows:
        return [], []
    columns = [cell.text for cell in rows[0].elements("th")][1:]
    members = []
    for row in rows[1:]:
        selects = list(row.elements("select"))
        members.append((row.text_with(lambda e: "" if e.tag == "select" else None), selects))
    return columns, members


def preferences_grid(as_client: Any, slug: str) -> tuple[list[str], list[tuple[str, list[str]]]]:
    """Members' preferences on Schedule settings: the slot of each column, and each row's member
    with the label that each of its selectors shows."""
    section = section_of(settings_page(as_client, slug), "Members' preferences")
    columns, rows = _preference_rows(section)
    assert columns or rows, section
    members = []
    for name, selects in rows:
        assert len(selects) == len(columns), (name, selects)
        members.append((name, [_selected(select)[1] for select in selects]))
    return columns, members


def preferences_stored(as_client: Any, slug: str) -> set[tuple[str, str, str]]:
    """The preferences of the association, as a manager's Members' preferences shows them: each
    member's name, the slot's column and the value of each selector not on "—"."""
    section = section_of(settings_page(as_client, slug), "Members' preferences")
    columns, rows = _preference_rows(section)
    stored = set()
    for name, selects in rows:
        for column, select in zip(columns, selects, strict=True):
            value = _selected(select)[0]
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
    return text_of(section_of(availability_page(as_client, slug), heading))


def availability_lines(as_client: Any, slug: str, heading: str) -> list[str]:
    """The lines that the `heading` section of My availability lists."""
    return lines_of(section_of(availability_page(as_client, slug), heading))


def add_absence(as_client: Any, planning: Planning, first: str, last: str) -> dict[str, Any]:
    """Adds an absence of the user's own with "Add an absence" on My availability."""
    return add_absence_of(as_client, planning.association, first, last)


def add_absence_of(
    as_client: Any, association: dict[str, Any], first: str, last: str
) -> dict[str, Any]:
    """Adds an absence of the user's own in `association` with "Add an absence" on My
    availability."""

    def add() -> None:
        text = shown(add_absence_on_screen(as_client, association["slug"], first, last))
        assert GENERIC not in text, text

    absence_id = added_id("absence", association["id"], add)
    return {"id": absence_id, "first": first, "last": last}


def write_note(as_client: Any, planning: Planning, text: str) -> None:
    """Saves the user's own note with "Note for the managers" on My availability."""
    shown_text = shown(save_note(as_client, planning.slug, text))
    assert GENERIC not in shown_text, shown_text


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


def _occurrence_text(item: Element) -> str:
    """What an occurrence or an obsolete registration shows, between brackets, a struck name
    between ~~."""
    struck = item.text_with(lambda e: f"~~{e.text}~~" if e.tag == "s" else None)
    return f"[{struck}]"


Week = tuple[str, list[str]]


def schedule_entries(fragment: str) -> list[str | Week]:
    """The lines and weeks a piece of the Schedule shows, in order: a line as its text; a week as
    its heading and the text of each of its days, e.g. ("Week 44", ["Thu 29 Oct [Chloé]",
    "Sat 31 Oct [~~Bruno~~]"]). A day is an element with role="group"; it shows its label, then
    a closure's "Closed" and label, then each occurrence or obsolete registration, an `<li>`,
    between brackets. A line is a `<p class="line">`, a week a `<section class="week">`."""
    entries: list[str | Week] = []
    for element in parse(fragment).elements():
        if element.tag == "p" and "line" in element.classes:
            entries.append(element.text)
        elif element.tag == "section" and "week" in element.classes:
            days = [
                day.text_with(lambda e: _occurrence_text(e) if e.tag == "li" else None)
                for day in element.elements()
                if day.get("role") == "group"
            ]
            entries.append((element.first("h2").text, days))
    return entries


def _day_group(fragment: str, day: str) -> Element:
    label = day_label(day)
    found = [e for e in parse(fragment).elements() if e.get("role") == "group"]
    found = [e for e in found if e.get("aria-label") == label]
    assert len(found) == 1, (day, fragment)
    return found[0]


def opens_menu(fragment: str, day: str) -> bool:
    """Whether the occurrence on `day` in the weeks of `fragment` can be clicked to open the
    menu: a button, not plain text."""
    return next(_day_group(fragment, day).elements("button"), None) is not None


def schedule_shown(as_client: Any, slug: str) -> list[str | Week]:
    """The lines and weeks the Schedule shows, as schedule_entries reads them."""
    return schedule_entries(part(schedule_page(as_client, slug), "main"))


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
    """The weeks the Schedule opens on without a planning period, as its actions get
    them."""
    return {"from": day_of_week("monday", -1), "to": day_of_week("sunday", 4)}


def open_menu(
    as_client: Any,
    slug: str,
    day: str,
    start: str,
    end: str,
    weeks: dict[str, str] | None = None,
) -> Any:
    """Clicks the occurrence, or the obsolete registration, of `day` from `start` to `end` on
    the Schedule, which shows `weeks` when given."""
    return as_client.post(
        f"/association/{slug}/menu", json={"date": day, "start": start, "end": end, **(weeks or {})}
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
    replacing: str | None = None,
) -> Any:
    """Clicks the display name of the member `user_id` in the menu of an occurrence, on a
    Schedule that shows `weeks`; with `replacing`, the id of the registration of the
    occurrence, confirms "Yes, give it" to the member instead."""
    extra = {} if replacing is None else {"replacing": replacing}
    return as_client.post(
        f"/association/{slug}/propose",
        json={
            "user_id": user_id,
            "date": day,
            "start": start,
            "end": end,
            **(weeks or opened_weeks()),
            **extra,
        },
    )


Name = tuple[str, list[str]]


def _icons(item: Element) -> list[Element]:
    """The icons of a name of a menu: the elements in it with an aria-label and a title."""
    return [e for e in item.elements() if e.has("aria-label") and e.has("title")]


def _menu_items(fragment: str) -> list[Element]:
    """The names of the menu in a piece of HTML: the `<li>` it shows."""
    return list(parse(fragment).elements("li"))


def menu_names(fragment: str) -> list[Name]:
    """The members' names a menu offers, in order: each one's text, its count included, e.g.
    "Alice (2)", and the text of each of its icons, e.g. ["Absent Mon 9 Nov 2026"]. A name is
    an `<li>` of the menu; an icon, an element in it with an aria-label, whose text is its title
    (its hover text, which is also its description)."""
    names: list[Name] = []
    for item in _menu_items(fragment):
        text = item.text_with(lambda e: "" if e.has("aria-label") else None)
        names.append((text, [icon.get("title") or "" for icon in _icons(item)]))
    return names


def icon_names_of(as_client: Any, slug: str, day: str, name: str) -> list[str]:
    """The accessible name of each icon of the name `name` in the menu of the occurrence of
    `day` from 10:00 to 13:00."""
    response = open_menu(as_client, slug, day, "10:00", "13:00")
    for item in _menu_items(patched(response)):
        if re.match(rf"{re.escape(name)}\b", item.text):
            return [icon.get("aria-label") or "" for icon in _icons(item)]
    raise AssertionError(f"no name {name}")


def names_offered(
    as_client: Any, slug: str, day: str, start: str = "10:00", end: str = "13:00"
) -> list[Name]:
    """The members' names the menu of the occurrence of `day` offers, as menu_names reads
    them."""
    response = open_menu(as_client, slug, day, start, end)
    assert response.status_code == 200
    return menu_names(patched(response))


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


def weeks_again(as_client: Any, slug: str, first: str, last: str) -> Any:
    """The weeks from `first` to `last` of a Schedule that shows them again once today changes
    or the screen shows again: a plain GET of the weeks as an HTML fragment, 401 when signed
    out."""
    return as_client.get(f"/association/{slug}/weeks-again", params={"from": first, "to": last})


def create_share_link(as_client: Any, slug: str) -> Any:
    """Clicks "Create a share link" on Schedule settings, confirming "Replace" when there is
    one."""
    return as_client.post(f"/association/{slug}/settings/share-link", json={})


def revoke_share_link(as_client: Any, slug: str) -> Any:
    """Confirms "Revoke the share link?" on Schedule settings."""
    return as_client.post(f"/association/{slug}/settings/share-link/revoke", json={})


_SHARED_URL = re.compile(r"https?://[^\s\"'<>]+/shared/([A-Za-z0-9_-]+)")


def share_link_shown(as_client: Any, slug: str) -> str | None:
    """The token of the link that the Share link section of Schedule settings shows, None when
    it shows none."""
    section = section_of(settings_page(as_client, slug), "Share link")
    tokens = set(_SHARED_URL.findall(text_of(section)))
    assert len(tokens) <= 1, section
    return tokens.pop() if tokens else None


def shared_token(planning: Planning) -> str:
    """Alice creates a share link on Schedule settings; returns the token of the link shown."""
    text = shown(create_share_link(planning.alice_client, planning.slug))
    assert GENERIC not in text, text
    token = share_link_shown(planning.alice_client, planning.slug)
    assert token, text
    return token


def shared_page(as_client: Any, token: str) -> Any:
    """Opens the share link of `token`."""
    return as_client.get(f"/shared/{token}")


def shared_weeks_again(as_client: Any, token: str, first: str, last: str) -> Any:
    """The weeks from `first` to `last` of a Shared schedule that shows them again once today
    changes: a plain GET of the weeks as an HTML fragment, 404 when the link is no longer
    valid."""
    return as_client.get(f"/shared/{token}/weeks-again", params={"from": first, "to": last})


def shared_weeks(as_client: Any, token: str, first: str, last: str) -> Any:
    """Clicks "More weeks" on a Shared schedule that shows the weeks from `first` to `last`."""
    return as_client.post(f"/shared/{token}/weeks", json={"from": first, "to": last})
