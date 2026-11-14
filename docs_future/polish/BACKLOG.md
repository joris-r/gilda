# Polish

Settles the defects and open choices found by the Datastar rewrite:
actions that run twice, stale pages, missing messages and warnings,
orders and displays.

## Outline

Each increment lists the entries it settles; its `future` increment
adds the sections it integrates.

1. Network retries: /ui/errors.
   - Datastar: after a network error, `@post` retries even once its dialog is cancelled, so a failed "Delete my account" could still go through after Cancel; `retry: 'never'` covers only HTTP errors, and only `retryMaxCount: 0` stops it, as the confirmation macro does.
   - Actions outside a confirmation (Sign out, Create an account, Forgot password…) still retry after a network error, so they could run twice.
   - My preferences: a selector retries after a network error, so a late retry could overwrite a newer choice on the same slot.
2. Failed saves: /planning/ui/schedule-settings,
   /planning/ui/my-availability, /planning/operations/add-absence,
   /planning/operations/edit-absence, /planning/operations/add-closure,
   /planning/operations/edit-closure (Schedule settings also carries,
   from Stale data, Members' preferences shown again when the screen
   shows again; both also carry, from Date order messages, the
   messages of a slot, the planning period, a closure or an absence
   that ends before it starts; from Warnings, Schedule settings
   carries the warnings of the slot and closure dialogs, and My
   availability, with Add absence and Edit absence, the refusal of an
   absence that overlaps another; from Past dates, Schedule settings
   lists only the closures ending today or later, and both screens,
   with Add closure, Edit closure, Add absence and Edit absence, carry
   the refusal of a closure or an absence that ends before today).
   - My preferences: when saving fails, the selector keeps the value chosen though it was not saved.
   - Members' preferences: when saving fails, the selector keeps the value chosen though it was not saved, as in My preferences.
3. Confirmation error: /ui/forms.
   - Confirmation: the generic error probably still shows after Cancel and reopening, until the next try.
4. Sign-in links: /core/operations/request-access-link,
   /core/operations/revoke-my-access-link,
   /core/operations/revoke-access-link, /core/ui/header,
   /core/ui/members, design/header.md, design/members.md.
   - Revoke my sign-in link: the menu offers it to a user who has no link, and then says "revoked"; consider showing it only when they have one.
   - Sign-in link: when the email can't be sent, the link is still created, so the member later shows "Revoke link" for a link nobody received.
   - Send link drops the link when the email can't be sent, but Sign-in link keeps it; align the two.
   - Revoke link from a page opened before the member's link was revoked elsewhere still says "revoked".
5. Access pages: /core/ui/access-link, /core/ui/confirm-email,
   design/access-link.md, design/confirm-email.md.
   - Access link and Confirm email: the page stays blank while the action runs, and after a server failure only the generic error shows, with no way forward.
6. New association: /design, design/new-association.md (the title:
   `/core/ui/header/title` as is; mockup, test and code to align; the
   design also carries, from Schedule display, the Schedule's columns
   for closed days and where the Occurrence menu opens).
   - New association: its mockup shows a title in the page, but `interface.md` says the header's location stands for the title; the page follows the mockup.
   - New association: "+ New association" is a link, while `interface.md` describes a button.
7. Orders: /readme, /ui/name-order, /home/ui/my-associations,
   /planning/ui/occurrence-menu, /planning/operations/register,
   design/my-associations.md (Members' order by display name follows
   /ui/name-order with no edit; the Occurrence menu also carries, from
   Stale days, its message shown until the next try or the menu
   closes, from Schedule display, its note icon's name, and, from
   Taken occurrences, a manager's names on a taken occurrence, giving
   it to another member, with Register's `replacing`).
   - My associations: the spec sets no order, so the list follows whatever order the database returns.
   - Members: display names are ordered by `casefold`, not by the language's collation, so "Émile" comes after "Zoé".
   - Manager's menu: names are ordered by `casefold`, not by the language's collation, as on Members.
8. Stale identifiers: /ui/changed-identifier (Members, kept in item
   4: Rename and Change the association identifier compare with the
   association as it now is, Delete with the name the screen shows).
   - Rename and Delete check against the name the page was loaded with: after a rename in another tab, Delete stays disabled for the new name until a reload.
   - Change the association identifier breaks every bookmark of the former URLs, with no redirect (`/core/operations/update-association/new-slug`).
   - Confirm and OK use the slug from page load, so after a change of identifier in another tab they show only the generic error.
9. Stale days: /planning/ui/schedule, /planning/ui/shared-schedule,
   /planning/operations/get-schedule (Occurrence menu, kept in item 7:
   a message shows until the next try or the menu closes; Schedule and
   Shared schedule also carry, from Stale data, the weeks shown again
   after "Someone took this slot in the meantime." and "This link is
   no longer valid." when More weeks or the new-day refresh is
   refused; from Schedule display, the Schedule shows the closed days
   that Get schedule now gives, and opens the Occurrence menu at once,
   loading its rest; from Taken occurrences, "This day is past." also
   shows in the confirmation of giving an occurrence to another
   member).
   - Schedule: a page left open past midnight keeps the old today line and past days until it reloads.
   - Schedule: a page left open past midnight still offers Sign up on yesterday's occurrences, which then shows only the generic error.
10. Stale data: /ui/notices.
    - Sign up: after "Someone took this slot in the meantime.", the Schedule still shows the occurrence as free until a reload.
    - Members' preferences: a member added on Members, or a choice made on My availability, shows only after a reload.
    - Shared schedule: once the link is replaced or revoked, More weeks on a page already open shows only the generic error, not "This link is no longer valid.".
    - The one-time notice is kept in the session, so it shows on whichever page loads next, even in another tab.
11. Date order messages: design/schedule-settings.md (Schedule
    settings and My availability, kept in item 2, carry its messages;
    the mockup also carries, from Warnings, the Delete slot
    confirmation and the Edit the slot warning).
    - Add a slot or Edit the slot with To not after From shows only the generic error; the former frontend said "Check the dates and times: the start comes before the end."
    - Planning period and closures with To before From show only the generic error, as Slots do.
    - Absences with To before From show only the generic error; the former frontend said "Check the dates: the start comes before the end." (its translation is gone with the former frontend's other leftovers).
12. Warnings: design/forms.md (Schedule settings and My
    availability, kept in item 2, carry its warnings and its overlap
    message; closures may still overlap, with no warning, as Schedule
    shows each covering closure's label).
    - Edit the slot and Delete the slot don't warn that the slot's registrations become obsolete, nor that deleting it deletes the members' preferences on it.
    - Add a closure, Edit the closure and Delete the closure don't warn that the registrations on the closed dates become obsolete, or stop being obsolete.
    - Closures may overlap each other, with no warning.
    - Absences may overlap each other, with no warning.
13. Past dates (Schedule settings and My availability, kept in item
    2, carry its listing of closures and its refusals; a past
    registration is already refused, by Change registration's past
    case and, from Stale days, "This day is past.").
    - Closures: past closures stay listed forever; they could be listed from those ending today on, as Absences are.
    - Adding or editing an absence that ends before today saves it, but it never shows, with no message.
    - Cancel registration: the server cancels a registration dated before today (`/planning/operations/change-registration/cancel` doesn't forbid it), though no menu opens there.
14. Schedule display: /planning/operations/set-note,
    design/schedule.md, design/occurrence-menu.md (the Schedule's
    closed days and the Occurrence menu's opening, kept in item 9, and
    the menu's note icon, kept in item 7; a note of only spaces already shows
    no note icon, by the Occurrence menu's note case; the menu's mockup
    also carries, from Taken occurrences, a manager's names on a taken
    occurrence and the confirmation of giving it to another member).
    - Schedule: a closure on a weekday with no column of the shown weeks doesn't show at all.
    - Schedule menu: it shows centred on the screen, not anchored to the occurrence.
    - Schedule menu: it opens only once the server answers, so a slow network shows nothing for a while after the click.
    - Note icon: the whole note is the icon's accessible name, so a long note gives a long screen-reader label.
    - A note of only spaces is saved as is; the Schedule's note icon (a later item) should treat it as empty.
15. Taken occurrences (the Occurrence menu and Register, kept in item
    7, carry a manager's names on a taken occurrence and giving it to
    another member; the Schedule, kept in item 9, its past message;
    the menu's mockup, kept in item 14, its two states).
    - Manager's menu: a taken occurrence offers no names, so moving it to another member takes a cancel, then a proposal.
16. Clipboard:
    - Share link: "Link copied." shows even when the browser refuses the clipboard.
17. Years on dates:
    - My associations shows dates without their year, so a proposal months ahead (e.g. "Sun 3 Jan") is ambiguous.

## Lessons

- New association: its integration drops the in-page title from the code and from the test of `/core/ui/new-association/form`, which asserts an `<h1>` "New association" in `main`; the "+ New association" link of My associations needs no code change.
- Orders: the code sorts names with `casefold` in two places (`core/pages.py` `members_in_order`, and the Occurrence menu's names in `planning/pages.py`); its integration may share one sort key in `web/`, used by My associations too; Members' preferences follows Members' order through `/planning/ui/schedule-settings/preferences-order`, with no change of its own.
- Orders: a section kept in an earlier item cannot cite a section a later item adds, or `docs/` is not closed after the earlier one; /ui/name-order is therefore stated for every screen that sorts by name, and Members' `[list]` (item 4) is left as is.
- Stale identifiers: an outline item may not cite by path a section kept in an earlier item, even in a parenthesis, or [outline] counts it in two increments; name it in plain text.
- Stale identifiers: every action of an association screen (Members, Schedule, Schedule settings, My availability, My associations' Confirm and OK) finds its association by the slug of its URL today (`detail_by_slug`); /ui/changed-identifier needs them to find it by its id instead, e.g. carried in the action's URL, as technical.md leaves those URLs free.
- Stale days: the weeks of the Schedule render the days before today with no menu button (`day.past` in `schedule_weeks.html`), and the menu's handler checks no date; the new-day refresh can reuse More weeks' handler with the shown range, and the shared one its own. The refresh also shows what changed elsewhere since the page opened, which Stale data (item 10) may build on.
- Date order messages: its messages went into Schedule settings and My availability, already kept by Failed saves (item 2), so Failed saves integrates and tests them; item 11 then integrates only the Add a slot mockup, whose times now differ so that "This slot already exists." can show with them.
- Warnings: a section kept in an earlier item that gains a message citing a new case of an operation pulls that operation into the earlier item: Add absence and Edit absence went to Failed saves (item 2) with My availability's overlap message, leaving Warnings (item 12) only `design/forms.md`.
- Past dates: all its statements went to Failed saves (item 2), with Add closure and Edit closure, as its messages sit in Schedule settings and My availability; item 13 integrates no section, so its entries are done once item 2 is, and it can then leave the outline. Its third entry was already settled in `docs/` before the outline (`/planning/operations/change-registration/past`, tested in `test_schedule_menu.py`), so item 14 onwards may also hold entries `docs/` already settles: check each against `docs/` first.
- Schedule display: where the Occurrence menu opens is already coded, with CSS anchor positioning (`restore-design`), centred as a last resort; it shows centred where the browser lacks anchor positioning, so the integration of item 6 needs a placement that works without it. Item 6 also brings the Schedule's columns for closed days before item 9 adds them to Get schedule: its code may compute them from the slots in `_weeks_view` (`planning/pages.py`, whose columns come from the occurrences and obsolete registrations alone).

## For the human

- Network retries: two saves of the same selector sent in quick succession (My preferences, Members' preferences) may still reach the server out of order, the older overwriting the newer; with no resend this needs a slow network and two changes within one request's time, so it is left unspecified.
- Failed saves: the outline must cite domain sections (`/planning/ui/…`) for [outline], but check.py's [depends] then reports them, as BACKLOG.md counts as the top level, which declares no domain; a false positive of the Dev43 plugin, worth an issue.
- Confirmation error: /ui/errors/kept ("What was typed stays.") does not say whether a form opened again after a failed try and Cancel keeps what was typed; /ui/forms/fresh settles only its messages, and the project backlog's Add a slot entry already touches the fields.
- Confirmation error: the Occurrence menu is not a dialog, so /ui/forms/fresh leaves open whether "Someone took this slot in the meantime." or the generic error still shows when it opens again on the same occurrence; outline item 9 or 10 may settle it. Settled by Stale days, in the Occurrence menu, so carried by Orders (item 7): opened again, the menu shows no message of an earlier try.
- Sign-in links: `design/header.md` shows no confirmation and no message of "Revoke my sign-in link" ("Your sign-in link is revoked.", and now "You have no sign-in link."), while `design/members.md` lists its messages; whether the header's messages need a mockup is left to the human.
- Access pages: when Confirm email succeeds on the server but its answer never reaches the browser, the token is gone, so [Try again] shows "This link is no longer valid." and "Create an account to request a new one", though the email is confirmed and the user can sign in with their password; left as is, as it needs a lost answer, but a pointer to Sign in there is the human's call.
- New association: without its in-page title, the page has no `<h1>`, as Schedule, Members, Schedule settings and My availability already, where only My associations' location is an `<h1>`; whether the location should be each signed-in screen's heading is left to the human (`/core/ui/header/title` says it stands for the title, not how).
- Orders: /ui/name-order ignores case and accents in every language, rather than a collation per interface language; for English and French names the two agree, and it needs no new dependency (e.g. PyICU), so a locale-aware collation is left to the human.
- Orders: My associations is sorted by name alone, not managers first as Members; whether the associations the user manages should come first is left to the human.
- Stale identifiers: a former slug still leads to Unknown association, with no redirect, as decided by `association-slug` (a redirect needs a history of slugs, a model change, and conflicts with `/core/operations/update-association/new-slug`, which frees the former slug for another association); left as is, a redirect is the human's call.
- Stale identifiers: Delete the association checks the typed name against the name the screen shows, not the association's current name, so a page opened before a rename in another tab deletes once the former name is typed; it is still the same association, so no server check (a `name` input of `/core/operations/delete-association`) was added.
- Stale identifiers: links of a screen opened before a change of identifier (the header's name, My associations' names, Choose your slots) are not actions on the association's data, so /ui/changed-identifier does not cover them: they may keep the former URL until the screen opens again, leading to Unknown association, or to another association that took the former slug; left free.
- Stale days: other screens keep the day they opened with past midnight (My availability's absences ending today or later, My associations' summary); no entry names them, so they are left as is.
- Stale days: after midnight between Sunday and Monday, an open Schedule keeps its weeks, so it shows one more past week than a fresh one (`/planning/operations/get-schedule/default`); its range is not recomputed.
- Stale days: "This day is past." also shows in the confirmation of Cancel registration, which `design/occurrence-menu.md` shows refused only in the plain menu ("Refused"); whether that state needs its own mockup is left to the human.
- Stale days: on a Shared schedule open past midnight whose link was since replaced or revoked, the new-day refresh leaves the page as it was, with no message, rather than "This link is no longer valid."; Stale data (item 10) may revise it with More weeks. Settled by Stale data: refused, the page shows only "This link is no longer valid.", as More weeks does.
- Stale data: Members' preferences shows again only when Schedule settings shows again after being hidden, so a choice a member makes while the manager keeps the screen in view shows only once they leave and come back, or reload; a refresh every minute, as the new-day one, was left out.
- Stale data: after "Someone took this slot in the meantime.", the Schedule behind shows the taker, but the open menu keeps "Sign up" (and a manager's names) until it closes, a new try giving the same message; whether the menu should then show the occurrence as it now is is left to the human.
- Stale data: `docs/README.md`'s line for ui.md, carried by Orders, names neither Changed identifier nor Notices, which later items add; the last of them to be integrated may add both.
- Stale data: when Schedule settings shows again, only Members' preferences shows again, so its columns may show a slot that SLOTS above does not list yet, or no longer lists, until a reload; refreshing the whole screen was left out to keep open dialogs and the volunteer's view out of it.
- Stale data: the third [soundness] check still reported findings on Members' preferences shown again (a save running then, a cell whose member or slot is gone, and the main case overlapping its sub-cases); `/planning/ui/schedule-settings/preferences-again` was then rewritten to wait until no save runs and as a numbered list whose last case is "Otherwise", which no check has re-read.
- Date order messages: a slot whose To is not after From shows "The end time must be after the start time.", and a planning period, closure or absence whose To is before From "The end date can't be before the start date.", in the dialog, as "This slot already exists."; the mockups show no new state, as `design/schedule-settings.md` already shows a message in the Add a slot dialog (its times changed from 09:00–09:00, which now gives the end time message, to 10:00–13:00, the slot listed), while `design/my-availability.md` shows no message in its absence dialogs, the generic error included; whether that state needs a mockup is left to the human.
- Warnings: the warnings are fixed sentences in the existing dialogs and confirmations, shown whether or not a registration or preference is affected, as Members' "Their upcoming registrations are cancelled."; they name only registrations from today on, though the same actions also make obsolete the past ones the Schedule shows in its past week; counts were left out, as the closure dialogs would need them recomputed while the dates are typed.
- Warnings: the closure warnings say registrations "may stop being obsolete", as a registration on a date the closure no longer covers stays obsolete when another closure covers it or its slot is gone; a precise count or list is the human's call.
- Warnings: "upcoming registrations" means dated today or later and not obsolete in `/home/operations/list-my-associations/upcoming`, but not cancelled in Members' Remove confirmation (`/core/ui/members/remove`); the warnings avoid the word and say "from today on".
- Warnings: overlapping absences are refused from now on, but no invariant forbids them, so absences saved before may still overlap from today on: which one the Occurrence menu's absence icon names (`/planning/ui/occurrence-menu/absent`, "the absence covering the date") is then left free, and Edit absence on either is refused until the edit removes the overlap; two requests at once may also both pass the check. An invariant, with a migration merging the overlapping absences, is the human's call.
- Warnings: overlapping closures stay allowed with no warning, as the Schedule's Closed line already lists the labels of every closure covering a day (e.g. an event within a holiday); a warning or a refusal is the human's call.
- Past dates: a closure or an absence that ends before today is refused ("The end date can't be before today."), rather than saved and kept out of the list, as neither then has any effect a member or manager can act on; a manager can therefore no longer record a closure after the fact to mark the past week's registrations obsolete, nor edit or delete a closure once it has ended (it no longer shows), which may touch the registration counts of a planning period that started before today; keeping past closures listed, or a "show past" toggle, is the human's call.
- Past dates: the backlog entry on cancelling a past registration was already settled when the outline was written: `/planning/operations/change-registration/past` refuses it, and the Stale days item shows "This day is past."; nothing was added for it.
- Past dates: the planning period may still be set wholly before today, and stays shown; it was left as is, as no entry names it.
- Schedule display: Set note now drops the leading and trailing spaces and line breaks, but notes saved before keep theirs, so one of only spaces still shows blank on My availability, where `/planning/ui/my-availability/none` gives "None" only to an empty note (the code already shows "None" for it); a migration trimming the stored notes is the human's call.
- Schedule display: the note icon is named "Note", the note being its description, rather than the note itself; the absence icon keeps its text as its name, as it is short.
- Schedule display: the menu opens at once with its title and a loading sign, the rest coming with the server's answer; an answer for an earlier click, or after the menu closed, is dropped. A closure's day on a weekday with no slot gets no column of its own, as it removes no opening.
- Schedule display: no operation of `docs/` names what the Occurrence menu loads (members, counts, absences, notes), a gap older than this feature; the menu's loading and its outcomes are stated on the Schedule's menu action alone (`/planning/ui/schedule/load`).
- Schedule display: the third [soundness] check of the menu's loading reported three points (a menu reopened on the same occurrence, when the past date is judged, and a load that fails never "loading"); `[opens]`, `[latest]` and `[load]` of `/planning/ui/schedule` were then rewritten per click, the past date judged when the load ends, which no check has re-read.
- Taken occurrences: a manager may give an occurrence away from a confirmed registration too, cancelling a member's commitment behind a confirmation; the member is not told, as the software sends no notice of registrations, and sees their name struck only on the Schedule (Get schedule shows the new registration, not the cancelled one); limiting it to proposed registrations, or telling the member, is the human's call.
- Taken occurrences: the move reuses Register with an optional `replacing`, so the cancellation and the new registration happen in one operation; a `replacing` that is no longer the occurrence's registration is refused as taken when another holds it, and registers normally when the occurrence has become free.
- Taken occurrences: `design/occurrence-menu.md` shows no refused state of the move's confirmation ("Someone took this slot in the meantime.", "This day is past."), as for Cancel registration's; whether they need a mockup is left to the human.
