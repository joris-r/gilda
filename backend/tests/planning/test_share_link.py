import html
import re
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import pytest
import time_machine

from tests.page import buttons_named, dialog_named, dialog_opened_by
from tests.planning.conftest import (
    GENERIC,
    Planning,
    add_closure_on_screen,
    create_share_link,
    day_in,
    day_of_week,
    headings_of,
    part,
    revoke_share_link,
    schedule_entries,
    schedule_shown,
    section_of,
    set_period,
    settings_page,
    settings_section,
    share_link_shown,
    shared_page,
    shared_token,
    shared_weeks,
    shared_weeks_again,
    shown,
    sign_up,
    text_of,
    unique_email,
)

NAME = "Jardin partagé des Lilas"
INVALID = "This link is no longer valid."
REPLACE = "Replace the share link? The current link no longer shows the Schedule."
REVOKE = "Revoke the share link? It no longer shows the Schedule."


def other_user(new_client: Callable[[], Any]) -> Any:
    """Zoé, signed in on her own client, who is not a member."""
    other = new_client()
    sign_up(other, "Zoé", unique_email("Zoe"))
    return other


def collapsed(fragment: str) -> str:
    return " ".join(text_of(fragment).split())


def share_section(as_client: Any, slug: str) -> str:
    """The text of the Share link section of Schedule settings, its title included."""
    return settings_section(as_client, slug, "Share link")


def shared(as_client: Any, token: str) -> str:
    """The page that the share link of `token` opens, which answers 200."""
    response = shared_page(as_client, token)
    assert response.status_code == 200
    return str(response.text)


def shows_the_schedule(token: str, as_client: Any) -> bool:
    """Whether the share link of `token` shows a Schedule, rather than "no longer valid"."""
    page = html.unescape(shared(as_client, token))
    if INVALID in page:
        assert "Week" not in text_of(part(page, "main")), page
        return False
    assert "More weeks" in text_of(part(page, "main")), page
    return True


# Schedule settings: Share link


class TestShareLink:
    # /planning/ui/schedule-settings/share-link
    # /planning/ui/schedule-settings/create-link
    def test_without_a_link_shows_none_and_create_a_share_link(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)

        section = share_section(client, planning.slug)

        assert "None" in section
        assert "Create a share link" in section
        assert "/shared/" not in section
        assert share_link_shown(client, planning.slug) is None

    # /planning/ui/schedule-settings/share-link
    # /planning/ui/schedule-settings/copy
    # /planning/ui/schedule-settings/revoke-link
    def test_shows_the_link_with_copy_and_its_delete_icon(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        token = shared_token(planning)

        section = section_of(settings_page(client, planning.slug), "Share link")

        assert re.search(rf"https?://\S+/shared/{re.escape(token)}", collapsed(section))
        assert "None" not in collapsed(section)
        assert re.search(r"<button[^>]*>\s*Copy\s*</button>", section)
        assert 'aria-label="Revoke the share link"' in section

    # /planning/ui/schedule-settings/share-link
    # /planning/ui/shared-schedule/shown
    def test_the_link_shown_opens_the_shared_schedule(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)

        token = shared_token(planning)

        assert shows_the_schedule(token, new_client())

    # /planning/model/sharelink/token
    def test_the_links_of_two_associations_differ(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        other = Planning(new_client(), new_client)

        assert shared_token(planning) != shared_token(other)

    # /planning/ui/schedule-settings/create-link
    def test_with_a_link_create_asks_to_replace_it(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        shared_token(planning)

        dialog = dialog_named(settings_page(client, planning.slug), REPLACE)

        assert re.search(r"<button[^>]*>\s*Replace\s*</button>", dialog.html)

    # /planning/ui/schedule-settings/revoke-link
    def test_its_delete_icon_asks_to_revoke_it(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        shared_token(planning)

        page = settings_page(client, planning.slug)

        [icon] = buttons_named(part(page, "main"), "Revoke the share link")
        dialog = dialog_opened_by(page, icon)
        assert dialog_named(page, REVOKE).get("id") == dialog.get("id")
        assert re.search(r"<button[^>]*>\s*Revoke\s*</button>", dialog.html)

    # /planning/ui/schedule-settings/share-link
    # /core/ui/header/language
    def test_in_french_it_is_lien_de_partage(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        client.cookies.set("language", "fr")

        section = settings_section(client, planning.slug, "Lien de partage")

        assert "Aucun" in section
        assert "Créer un lien de partage" in section

    # /planning/ui/schedule-settings/share-link
    def test_comes_after_slots_and_before_members_preferences(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)

        headings = re.findall(
            r"<h2[^>]*>\s*(.*?)\s*</h2>",
            part(html.unescape(settings_page(client, planning.slug)), "main"),
        )

        assert headings.index("Slots") < headings.index("Share link")
        assert headings.index("Share link") < headings.index("Members' preferences")

    # /planning/ui/schedule-settings/share-link
    # /planning/ui/schedule-settings/volunteer
    def test_a_volunteer_does_not_see_it(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        token = shared_token(planning)

        page = html.unescape(settings_page(planning.bruno_client, planning.slug))

        assert "Share link" not in page
        assert "Create a share link" not in page
        assert token not in page
        assert REVOKE not in page


class TestCreatingAShareLink:
    # /planning/ui/schedule-settings/create-link
    # /planning/operations/create-share-link/created
    def test_creates_it_and_the_screen_shows_it_at_once(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)

        text = shown(create_share_link(client, planning.slug))

        assert GENERIC not in text
        token = share_link_shown(client, planning.slug)
        assert token
        assert f"/shared/{token}" in text
        assert shows_the_schedule(token, new_client())

    # /planning/operations/create-share-link/created
    # /planning/ui/shared-schedule/invalid
    # /planning/model/sharelink/single
    def test_replaces_the_previous_link(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        previous = shared_token(planning)

        text = shown(create_share_link(client, planning.slug))

        token = share_link_shown(client, planning.slug)
        assert token and token != previous
        assert f"/shared/{token}" in text
        assert f"/shared/{previous}" not in text
        assert shows_the_schedule(token, new_client())
        assert not shows_the_schedule(previous, new_client())

    # /planning/operations/create-share-link/manager
    def test_a_volunteer_creates_nothing(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)

        response = create_share_link(planning.bruno_client, planning.slug)

        assert "/shared/" not in response.text
        assert share_link_shown(client, planning.slug) is None

    # /planning/operations/create-share-link/manager
    def test_a_volunteer_replaces_nothing(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        token = shared_token(planning)

        create_share_link(planning.bruno_client, planning.slug)

        assert share_link_shown(client, planning.slug) == token
        assert shows_the_schedule(token, new_client())

    # /planning/operations/create-share-link/manager
    def test_a_non_member_creates_nothing(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)

        response = create_share_link(other_user(new_client), planning.slug)

        assert "/shared/" not in response.text
        assert share_link_shown(client, planning.slug) is None

    # /core/ui/access/action
    def test_signed_out_leads_to_sign_in_and_creates_nothing(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)

        text = shown(create_share_link(new_client(), planning.slug))

        assert "window.location" in text
        assert share_link_shown(client, planning.slug) is None


class TestRevokingTheShareLink:
    # /planning/ui/schedule-settings/revoke-link
    # /planning/ui/schedule-settings/share-link
    # /planning/operations/revoke-share-link/revoked
    # /planning/ui/shared-schedule/invalid
    def test_revokes_it_and_the_screen_shows_none_at_once(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        token = shared_token(planning)

        text = shown(revoke_share_link(client, planning.slug))

        assert GENERIC not in text
        assert "None" in text
        assert token not in text
        assert share_link_shown(client, planning.slug) is None
        assert not shows_the_schedule(token, new_client())

    # /planning/operations/create-share-link/created
    def test_a_link_created_after_revoking_works(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        shared_token(planning)
        shown(revoke_share_link(client, planning.slug))

        token = shared_token(planning)

        assert shows_the_schedule(token, new_client())

    # /planning/operations/revoke-share-link/manager
    def test_a_volunteer_revokes_nothing(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        token = shared_token(planning)

        revoke_share_link(planning.bruno_client, planning.slug)

        assert share_link_shown(client, planning.slug) == token
        assert shows_the_schedule(token, new_client())

    # /planning/operations/revoke-share-link/manager
    def test_a_non_member_revokes_nothing(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        token = shared_token(planning)

        revoke_share_link(other_user(new_client), planning.slug)

        assert shows_the_schedule(token, new_client())

    # /core/ui/access/action
    def test_signed_out_leads_to_sign_in_and_revokes_nothing(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        token = shared_token(planning)

        text = shown(revoke_share_link(new_client(), planning.slug))

        assert "window.location" in text
        assert shows_the_schedule(token, new_client())


# Shared schedule


def filled(planning: Planning) -> None:
    """Thursday and Saturday slots, Bruno confirmed and Chloé proposed next week, a cancelled
    registration and a closure the week after, and a planning period."""
    planning.add_slot("thursday", "10:00", "13:00")
    planning.add_slot("saturday", "10:00", "13:00")
    planning.registered(
        planning.bruno_client, planning.bruno, day_of_week("thursday"), "10:00", "13:00"
    )
    planning.registered(
        planning.alice_client, planning.chloe, day_of_week("saturday"), "10:00", "13:00"
    )
    later = planning.registered(
        planning.chloe_client, planning.chloe, day_of_week("thursday", 2), "10:00", "13:00"
    )
    planning.cancel(planning.chloe_client, later)
    saturday = day_of_week("saturday", 2)
    text = shown(add_closure_on_screen(planning.alice_client, planning.slug, saturday, saturday))
    assert GENERIC not in text, text
    monday, sunday = day_of_week("monday"), day_of_week("sunday")
    period = shown(set_period(planning.alice_client, planning.slug, monday, sunday))
    assert GENERIC not in period, period


def shared_entries(as_client: Any, token: str) -> Any:
    return schedule_entries(part(shared(as_client, token), "main"))


class TestSharedSchedule:
    # /planning/ui/shared-schedule/shown
    # /planning/ui/shared-schedule/status
    # /planning/operations/get-shared-schedule/schedule
    def test_signed_out_shows_the_schedule_as_a_member_sees_it(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        filled(planning)
        token = shared_token(planning)

        entries = shared_entries(new_client(), token)

        assert entries == schedule_shown(planning.bruno_client, planning.slug)
        assert day_in(entries, day_of_week("thursday")) == "[Bruno]"
        assert day_in(entries, day_of_week("saturday")) == "[Chloé ?]"
        assert day_in(entries, day_of_week("thursday", 2)) == "[~~Chloé~~]"
        assert day_in(entries, day_of_week("saturday", 2)) == "Closed"

    # /planning/ui/shared-schedule/shown
    # /planning/operations/get-shared-schedule/schedule
    def test_works_signed_in_as_a_non_member(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        filled(planning)
        token = shared_token(planning)

        entries = shared_entries(other_user(new_client), token)

        assert entries == schedule_shown(planning.bruno_client, planning.slug)

    # /planning/ui/shared-schedule/shown
    # /planning/operations/get-shared-schedule/schedule
    def test_works_signed_in_as_a_member(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        filled(planning)
        token = shared_token(planning)

        entries = shared_entries(planning.bruno_client, token)

        assert entries == schedule_shown(planning.bruno_client, planning.slug)

    # /planning/operations/get-shared-schedule/schedule
    # /planning/ui/schedule/empty
    def test_shows_only_its_association(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        other = Planning(new_client(), new_client)
        other.add_slot("thursday", "10:00", "13:00")
        token = shared_token(planning)

        main = text_of(part(shared(new_client(), token), "main"))

        assert "No openings in these weeks." in main

    # /planning/ui/shared-schedule/shown
    def test_without_the_links_to_the_other_screens_and_with_no_menu(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        filled(planning)
        token = shared_token(planning)

        for as_client in (new_client(), client):
            page = html.unescape(shared(as_client, token))
            assert f"/association/{planning.slug}" not in page
            main = text_of(part(page, "main"))
            for screen in ("My availability", "Members", "Schedule settings", "Sign up"):
                assert screen not in main

    # /planning/ui/shared-schedule/shown
    # /planning/ui/schedule/weeks
    def test_more_weeks_is_at_the_end(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")
        token = shared_token(planning)

        main = part(shared(new_client(), token), "main")

        button = re.search(r"<button[^>]*>\s*More weeks\s*</button>", main)
        assert button
        assert main.rfind("</section>") < button.start()

    # /planning/ui/shared-schedule/shown
    # /core/ui/header/language
    def test_follows_the_language(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")
        token = shared_token(planning)
        visitor = new_client()
        visitor.cookies.set("language", "fr")

        page = html.unescape(shared(visitor, token))

        headings = headings_of(schedule_entries(page))
        assert headings and all(h.startswith("Semaine ") for h in headings)
        assert "Plus de semaines" in page


class TestSharedScheduleHeader:
    # /core/ui/header/shared
    def test_shows_the_association_name_leading_nowhere_and_the_language_selector(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        token = shared_token(planning)

        header = part(html.unescape(shared(new_client(), token)), "header")

        assert NAME in collapsed(header)
        assert not re.search(rf"<a[^>]*>\s*{re.escape(NAME)}\s*</a>", header)
        assert "English" in header
        assert "Français" in header

    # /core/ui/header/shared
    def test_signed_in_it_shows_the_same_without_the_users_menu(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        token = shared_token(planning)

        page = html.unescape(shared(client, token))
        header = part(page, "header")

        assert NAME in collapsed(header)
        assert not re.search(rf"<a[^>]*>\s*{re.escape(NAME)}\s*</a>", header)
        assert "English" in header
        assert "Alice" not in collapsed(header)
        assert "Sign out" not in page
        assert "Delete my account" not in page


class TestSharedScheduleNoLongerValid:
    # /planning/ui/shared-schedule/invalid
    # /planning/ui/shared-schedule/status
    # /planning/operations/get-shared-schedule/unknown
    @pytest.mark.parametrize("token", ["unknown-token", "Hq3v"])
    def test_an_unknown_link_says_so(self, client: Any, token: str) -> None:
        page = html.unescape(shared(client, token))

        assert INVALID in text_of(part(page, "main"))
        assert "Page not found" not in page
        assert "Week" not in page

    # /planning/ui/shared-schedule/invalid
    # /planning/operations/create-share-link/created
    def test_a_replaced_link_says_so(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")
        previous = shared_token(planning)
        shared_token(planning)

        assert not shows_the_schedule(previous, new_client())

    # /planning/ui/shared-schedule/invalid
    # /planning/ui/shared-schedule/status
    # /planning/operations/revoke-share-link/revoked
    def test_a_revoked_link_says_so(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")
        token = shared_token(planning)
        shown(revoke_share_link(client, planning.slug))

        page = html.unescape(shared(new_client(), token))

        assert INVALID in page
        assert NAME not in page

    # /planning/ui/shared-schedule/invalid
    # /core/ui/header/language
    def test_follows_the_language(self, client: Any) -> None:
        client.cookies.set("language", "fr")

        assert "Ce lien n'est plus valide." in html.unescape(shared(client, "unknown-token"))


class TestSharedMoreWeeks:
    # /planning/ui/shared-schedule/shown
    # /planning/ui/schedule/more
    def test_adds_the_four_weeks_that_follow(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")
        late = day_of_week("thursday", 7)
        planning.registered(planning.bruno_client, planning.bruno, late, "10:00", "13:00")
        token = shared_token(planning)

        text = shown(
            shared_weeks(new_client(), token, day_of_week("monday", -1), day_of_week("sunday", 4))
        )

        entries = schedule_entries(text)
        assert len(headings_of(entries)) == 10
        assert day_in(entries, late) == "[Bruno]"
        assert re.search(r"<button[^>]*>\s*More weeks\s*</button>", text)

    # /planning/ui/shared-schedule/shown
    def test_the_weeks_added_open_no_menu(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")
        token = shared_token(planning)

        text = shown(
            shared_weeks(new_client(), token, day_of_week("monday", -1), day_of_week("sunday", 4))
        )

        assert f"/association/{planning.slug}" not in text

    # /planning/ui/shared-schedule/shown
    # /core/ui/header/language
    def test_follows_the_language(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")
        token = shared_token(planning)
        visitor = new_client()
        visitor.cookies.set("language", "fr")

        text = shown(
            shared_weeks(visitor, token, day_of_week("monday", -1), day_of_week("sunday", 4))
        )

        headings = headings_of(schedule_entries(text))
        assert headings and all(h.startswith("Semaine ") for h in headings)
        assert "Plus de semaines" in text

    # /ui/errors/generic
    @pytest.mark.parametrize(
        "body",
        [
            {"to": "2026-12-13"},
            {"from": "2026-11-02"},
            {"from": "2026-11-02", "to": "13/12/2026"},
            {"from": "2026-12-13", "to": "2026-11-02"},
        ],
    )
    def test_a_missing_or_invalid_range_shows_the_generic_error(
        self, client: Any, new_client: Callable[[], Any], body: dict[str, Any]
    ) -> None:
        planning = Planning(client, new_client)
        token = shared_token(planning)

        text = shown(new_client().post(f"/shared/{token}/weeks", json=body))

        assert GENERIC in text
        assert "Week" not in text

    # /planning/operations/get-shared-schedule/unknown
    # /planning/operations/revoke-share-link/revoked
    # /planning/ui/shared-schedule/gone
    def test_a_revoked_link_shows_none_of_the_weeks(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")
        planning.registered(
            planning.bruno_client, planning.bruno, day_of_week("thursday"), "10:00", "13:00"
        )
        token = shared_token(planning)
        shown(revoke_share_link(client, planning.slug))

        response = shared_weeks(new_client(), token, day_of_week("monday"), day_of_week("sunday"))

        assert "Bruno" not in response.text
        assert "Week" not in response.text

    # /planning/ui/shared-schedule/gone
    # /planning/ui/shared-schedule/invalid
    @pytest.mark.parametrize("how", ["revoked", "replaced", "unknown"])
    def test_more_weeks_on_a_link_that_is_gone_shows_that_it_is_no_longer_valid(
        self, client: Any, new_client: Callable[[], Any], how: str
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")
        token = shared_token(planning)
        if how == "revoked":
            shown(revoke_share_link(client, planning.slug))
        elif how == "replaced":
            shared_token(planning)
        else:
            token = "unknown-token"

        text = shown(
            shared_weeks(new_client(), token, day_of_week("monday", -1), day_of_week("sunday", 4))
        )

        assert INVALID in text
        assert GENERIC not in text
        assert not headings_of(schedule_entries(text))

    # /planning/ui/shared-schedule/gone
    # /core/ui/header/language
    def test_the_message_of_a_gone_link_follows_the_language(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        token = shared_token(planning)
        shown(revoke_share_link(client, planning.slug))
        visitor = new_client()
        visitor.cookies.set("language", "fr")

        text = shown(
            shared_weeks(visitor, token, day_of_week("monday", -1), day_of_week("sunday", 4))
        )

        assert "Ce lien n'est plus valide." in text


class TestSharedWeeksAgain:
    """The weeks shown again once today changes, on a Shared schedule that stays open."""

    NOW = datetime(2026, 11, 8, 23, 30, tzinfo=UTC)
    FIRST, LAST = "2026-11-02", "2026-12-13"

    # /planning/ui/shared-schedule/new-day
    # /planning/operations/get-shared-schedule/schedule
    def test_shows_the_same_weeks_as_they_now_are(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")
        token = shared_token(planning)
        with time_machine.travel(self.NOW, tick=False):
            planning.registered(
                planning.chloe_client, planning.chloe, "2026-11-12", "10:00", "13:00"
            )

            response = shared_weeks_again(new_client(), token, self.FIRST, self.LAST)

        assert response.status_code == 200
        entries = schedule_entries(response.text)
        assert len(headings_of(entries)) == 6
        assert day_in(entries, "2026-11-12") == "[Chloé]"
        assert "Today · Monday 9 November 2026" in entries
        assert f"/association/{planning.slug}" not in response.text

    # /planning/ui/shared-schedule/new-day
    # /planning/ui/schedule/new-day
    def test_keeps_the_weeks_added_and_follows_the_new_today(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")
        token = shared_token(planning)

        with time_machine.travel(datetime(2026, 11, 12, 23, 30, tzinfo=UTC), tick=False):
            response = shared_weeks_again(new_client(), token, self.FIRST, "2027-01-10")

        entries = schedule_entries(response.text)
        assert len(headings_of(entries)) == 10
        assert "Today · Friday 13 November 2026" in entries
        assert "<button" not in re.sub(r"<button[^>]*>\s*More weeks\s*</button>", "", response.text)

    # /planning/ui/shared-schedule/new-day
    # /planning/ui/shared-schedule/gone
    @pytest.mark.parametrize("how", ["revoked", "replaced", "unknown"])
    def test_a_link_that_is_gone_is_refused_as_unknown(
        self, client: Any, new_client: Callable[[], Any], how: str
    ) -> None:
        planning = Planning(client, new_client)
        token = shared_token(planning)
        if how == "revoked":
            shown(revoke_share_link(client, planning.slug))
        elif how == "replaced":
            shared_token(planning)
        else:
            token = "unknown-token"

        response = shared_weeks_again(new_client(), token, self.FIRST, self.LAST)

        assert response.status_code == 404
        assert "Week" not in response.text

    # /planning/ui/shared-schedule/new-day
    # /planning/operations/get-schedule/reversed
    def test_reversed_dates_fail_without_saying_it_is_gone(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        token = shared_token(planning)

        response = shared_weeks_again(new_client(), token, self.LAST, self.FIRST)

        assert response.status_code >= 400
        assert response.status_code != 404
        assert "Week" not in response.text


class TestSharedClosedDays:
    # /planning/ui/schedule/closed-days
    # /planning/ui/shared-schedule/shown
    def test_a_closed_day_shows_as_a_member_sees_it(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")
        planning.add_slot("saturday", "10:00", "13:00")
        token = shared_token(planning)

        with time_machine.travel(datetime(2026, 11, 8, 23, 30, tzinfo=UTC), tick=False):
            planning.add_closure("2026-11-06", "2026-12-13", "Vacances")
            entries = shared_entries(new_client(), token)
            members = schedule_shown(planning.bruno_client, planning.slug)

        assert entries == members
        assert day_in(entries, "2026-11-07") == "Closed Vacances"
        assert day_in(entries, "2026-12-12") == "Closed Vacances"
        assert day_in(entries, "2026-11-05") == "[]"
