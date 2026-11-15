# Polish

Settles the defects and open choices found by the Datastar rewrite:
actions that run twice, stale pages, missing messages and warnings,
orders and displays.

## Outline

Each increment lists the sections it integrates, then the entries it
settles.

5. Name order and My associations: /readme, /ui/name-order,
   /home/ui/my-associations, design/my-associations.md (Members follows
   the rule with no edit of its own).
   - My associations: the spec sets no order, so the list follows whatever order the database returns.
   - Members: display names are ordered by `casefold`, not by the language's collation, so "Émile" comes after "Zoé".
   - My associations shows dates without their year, so a proposal months ahead (e.g. "Sun 3 Jan") is ambiguous.
6. Changed identifier: /ui/changed-identifier.
   - Change the association identifier breaks every bookmark of the former URLs, with no redirect (`/core/operations/update-association/new-slug`).
   - Confirm and OK use the slug from page load, so after a change of identifier in another tab they show only the generic error.
7. Notices: /ui/notices.
   - The one-time notice is kept in the session, so it shows on whichever page loads next, even in another tab.
8. My availability: /planning/ui/my-availability,
   /planning/operations/add-absence, /planning/operations/edit-absence.
   - My preferences: when saving fails, the selector keeps the value chosen though it was not saved.
   - Absences with To before From show only the generic error; the former frontend said "Check the dates: the start comes before the end." (its translation is gone with the former frontend's other leftovers).
   - Absences may overlap each other, with no warning.
   - Adding or editing an absence that ends before today saves it, but it never shows, with no message.
9. Schedule settings: /planning/ui/schedule-settings,
   /planning/operations/add-closure, /planning/operations/edit-closure,
   design/schedule-settings.md, design/forms.md (closures may still
   overlap, with no warning, as Schedule shows each covering closure's
   label).
   - Members' preferences: when saving fails, the selector keeps the value chosen though it was not saved, as in My preferences.
   - Members' preferences: a member added on Members, or a choice made on My availability, shows only after a reload.
   - Add a slot or Edit the slot with To not after From shows only the generic error; the former frontend said "Check the dates and times: the start comes before the end."
   - Planning period and closures with To before From show only the generic error, as Slots do.
   - Edit the slot and Delete the slot don't warn that the slot's registrations become obsolete, nor that deleting it deletes the members' preferences on it.
   - Add a closure, Edit the closure and Delete the closure don't warn that the registrations on the closed dates become obsolete, or stop being obsolete.
   - Closures may overlap each other, with no warning.
   - Closures: past closures stay listed forever; they could be listed from those ending today on, as Absences are.
   - Share link: "Link copied." shows even when the browser refuses the clipboard.
10. Occurrence menu: /planning/ui/occurrence-menu,
    /planning/operations/register, /planning/operations/set-note (a
    note of only spaces already shows no note icon, by the menu's note
    case; the menu's mockup comes with item 11).
    - Manager's menu: names are ordered by `casefold`, not by the language's collation, as on Members.
    - Manager's menu: a taken occurrence offers no names, so moving it to another member takes a cancel, then a proposal.
    - Note icon: the whole note is the icon's accessible name, so a long note gives a long screen-reader label.
    - A note of only spaces is saved as is; the Schedule's note icon (a later item) should treat it as empty.
11. Schedule: /planning/ui/schedule, /planning/ui/shared-schedule,
    /planning/operations/get-schedule, /design, design/schedule.md,
    design/occurrence-menu.md (a past registration is already refused,
    by Change registration's past case; this item adds its message).
    - Schedule: a page left open past midnight keeps the old today line and past days until it reloads.
    - Schedule: a page left open past midnight still offers Sign up on yesterday's occurrences, which then shows only the generic error.
    - Sign up: after "Someone took this slot in the meantime.", the Schedule still shows the occurrence as free until a reload.
    - Shared schedule: once the link is replaced or revoked, More weeks on a page already open shows only the generic error, not "This link is no longer valid.".
    - Schedule: a closure on a weekday with no column of the shown weeks doesn't show at all.
    - Schedule menu: it shows centred on the screen, not anchored to the occurrence.
    - Schedule menu: it opens only once the server answers, so a slow network shows nothing for a while after the click.
    - Cancel registration: the server cancels a registration dated before today (`/planning/operations/change-registration/cancel` doesn't forbid it), though no menu opens there.

## Lessons

- Orders: the code sorts names with `casefold` in two places (`core/pages.py` `members_in_order`, and the Occurrence menu's names in `planning/pages.py`); its integration may share one sort key in `web/`, used by My associations too; Members' preferences follows Members' order through `/planning/ui/schedule-settings/preferences-order`, with no change of its own.
- Orders: a section kept in an earlier item cannot cite a section a later item adds, or `docs/` is not closed after the earlier one; /ui/name-order is therefore stated for every screen that sorts by name, and Members' `[list]` (item 4) is left as is.
- Stale identifiers: an outline item may not cite by path a section kept in an earlier item, even in a parenthesis, or [outline] counts it in two increments; name it in plain text.
- Stale identifiers: every action of an association screen (Members, Schedule, Schedule settings, My availability, My associations' Confirm and OK) finds its association by the slug of its URL today (`detail_by_slug`); /ui/changed-identifier needs them to find it by its id instead, e.g. carried in the action's URL, as technical.md leaves those URLs free.
- Stale days: the weeks of the Schedule render the days before today with no menu button (`day.past` in `schedule_weeks.html`), and the menu's handler checks no date; the new-day refresh can reuse More weeks' handler with the shown range, and the shared one its own. The refresh also shows what changed elsewhere since the page opened, which Stale data's statements on the Schedule, in the same increment (item 11), build on.
- Date order messages: its messages went into Schedule settings and My availability, so My availability (item 8) and Schedule settings (item 9) integrate and test them, item 9 with the Add a slot mockup, whose times now differ so that "This slot already exists." can show with them.
- Warnings: a section kept in an earlier item that gains a message citing a new case of an operation pulls that operation into the earlier item: Add absence and Edit absence go with My availability (item 8) for its overlap message.
- Past dates: its statements sit in My availability and Schedule settings, which carry them with Add absence and Edit absence (item 8) and Add closure and Edit closure (item 9). Its third entry was already settled in `docs/` before the outline (`/planning/operations/change-registration/past`, tested in `test_schedule_menu.py`), so other entries may also be settled by `docs/` already: check each against `docs/` first.
- Schedule display: where the Occurrence menu opens is already coded, with CSS anchor positioning (`restore-design`), centred as a last resort; it shows centred where the browser lacks anchor positioning, so the integration of design.md (item 11) needs a placement that works without it. Item 11 also brings the Schedule's columns for closed days, with Get schedule's closed days: `_weeks_view` (`planning/pages.py`) computes its columns from the occurrences and obsolete registrations alone.
- Dialogs: every opener of a dialog or confirmation must reset `$_failed` (`data-on:click="$_failed = false"`), as `/ui/forms/fresh` requires; later items (My availability, Schedule settings, Occurrence menu) rely on it, and their tests must target the dialog, not `main`, since the hidden dialogs sit inside `main`.
- Access pages: a page that runs its action on opening shows its running text under `!$_failed` and its [Try again] in the layout's `after_error` block, so that the invalid answer replacing the page's div leaves no button (the button hides once `$_failed` is false). Later items with an action on opening can reuse the block.
- Sign-in links: an outline item that gives an operation a new outcome (Revoke my sign-in link's "none") needs the existing tests that took the old default reworked (a user with no link used to get "revoked"); five backend tests and the e2e menu tests had to give the user a link first.
- Sign-in links: when a change removes or makes conditional an element a screen shows, search the tests by its visible text too ("Revoke my sign-in link" in the menu tests, in both languages).
- Sign-in links: the header's user menu reads `user.has_access_link` on every page, so later items needing the user's link state need no per-page context.

## For the human

- Sign-in links: Delete the association's "<name> is deleted." (`/core/ui/members/deleted-name`) uses the name the screen shows, the one Delete checks, so the UI holds it though Delete association returns no name; after a rename in another tab it is the former name.
- Sign-in links: `/core/ui/members` [renamed], [same-name], [slug-changed] and [same-slug] branch on the association's current name or slug, a condition on the model that `ui.md` states while Update association has no same-value case; a placement point for the human to rule on.
- Sign-in links: [leaves] (`/core/ui/header/leaves`) and [link-leaves] (`/core/ui/members/link-leaves`) follow from the item's condition and the link's deletion, and "in every association they belong to" (`/core/operations/revoke-access-link/revoked`) has no effect, as an AccessLink belongs to a user; all left as is.
- Network retries: two saves of the same selector sent in quick succession (My preferences, Members' preferences) may still reach the server out of order, the older overwriting the newer; with no resend this needs a slow network and two changes within one request's time, so it is left unspecified.
- Failed saves: the outline must cite domain sections (`/planning/ui/…`) for [outline], but check.py's [depends] then reports them, as BACKLOG.md counts as the top level, which declares no domain; a false positive of the Dev43 plugin, worth an issue.
- Confirmation error: /ui/errors/kept ("What was typed stays.") does not say whether a form opened again after a failed try and Cancel keeps what was typed; /ui/forms/fresh settles only its messages, and the project backlog's Add a slot entry already touches the fields.
- Confirmation error: the Occurrence menu is not a dialog, so /ui/forms/fresh leaves open whether "Someone took this slot in the meantime." or the generic error still shows when it opens again on the same occurrence; a later item may settle it. Settled by Stale days, in the Occurrence menu, so carried by Occurrence menu (item 10): opened again, the menu shows no message of an earlier try.
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
- Stale days: on a Shared schedule open past midnight whose link was since replaced or revoked, the new-day refresh leaves the page as it was, with no message, rather than "This link is no longer valid."; Stale data may revise it with More weeks. Settled by Stale data: refused, the page shows only "This link is no longer valid.", as More weeks does.
- Stale data: Members' preferences shows again only when Schedule settings shows again after being hidden, so a choice a member makes while the manager keeps the screen in view shows only once they leave and come back, or reload; a refresh every minute, as the new-day one, was left out.
- Stale data: after "Someone took this slot in the meantime.", the Schedule behind shows the taker, but the open menu keeps "Sign up" (and a manager's names) until it closes, a new try giving the same message; whether the menu should then show the occurrence as it now is is left to the human.
- Stale data: `docs/README.md`'s line for ui.md, carried by Name order and My associations (item 5), names neither Changed identifier nor Notices, which later items (6 and 7) add; the last of them to be integrated may add both.
- Stale data: when Schedule settings shows again, only Members' preferences shows again, so its columns may show a slot that SLOTS above does not list yet, or no longer lists, until a reload; refreshing the whole screen was left out to keep open dialogs and the volunteer's view out of it.
- Stale data: the third [soundness] check still reported findings on Members' preferences shown again (a save running then, a cell whose member or slot is gone, and the main case overlapping its sub-cases); `/planning/ui/schedule-settings/preferences-again` was then rewritten to wait until no save runs and as a numbered list whose last case is "Otherwise", which no check has re-read.
- Date order messages: a slot whose To is not after From shows "The end time must be after the start time.", and a planning period, closure or absence whose To is before From "The end date can't be before the start date.", in the dialog, as "This slot already exists."; the mockups show no new state, as `design/schedule-settings.md` already shows a message in the Add a slot dialog (its times changed from 09:00–09:00, which now gives the end time message, to 10:00–13:00, the slot listed), while `design/my-availability.md` shows no message in its absence dialogs, the generic error included; whether that state needs a mockup is left to the human.
- Warnings: the warnings are fixed sentences in the existing dialogs and confirmations, shown whether or not a registration or preference is affected, as Members' "Their upcoming registrations are cancelled."; they name only registrations from today on, though the same actions also make obsolete the past ones the Schedule shows in its past week; counts were left out, as the closure dialogs would need them recomputed while the dates are typed.
- Warnings: the closure warnings say registrations "may stop being obsolete", as a registration on a date the closure no longer covers stays obsolete when another closure covers it or its slot is gone; a precise count or list is the human's call.
- Warnings: "upcoming registrations" means dated today or later and not obsolete in `/home/operations/list-my-associations/upcoming`, but not cancelled in Members' Remove confirmation (`/core/ui/members/remove`); the warnings avoid the word and say "from today on".
- Warnings: overlapping absences are refused from now on, but no invariant forbids them, so absences saved before may still overlap from today on: which one the Occurrence menu's absence icon names (`/planning/ui/occurrence-menu/absent`, "the absence covering the date") is then left free, and Edit absence on either is refused until the edit removes the overlap; two requests at once may also both pass the check. An invariant, with a migration merging the overlapping absences, is the human's call.
- Warnings: overlapping closures stay allowed with no warning, as the Schedule's Closed line already lists the labels of every closure covering a day (e.g. an event within a holiday); a warning or a refusal is the human's call.
- Past dates: a closure or an absence that ends before today is refused ("The end date can't be before today."), rather than saved and kept out of the list, as neither then has any effect a member or manager can act on; a manager can therefore no longer record a closure after the fact to mark the past week's registrations obsolete, nor edit or delete a closure once it has ended (it no longer shows), which may touch the registration counts of a planning period that started before today; keeping past closures listed, or a "show past" toggle, is the human's call.
- Past dates: the backlog entry on cancelling a past registration was already settled when the outline was written: `/planning/operations/change-registration/past` refuses it, and the Schedule item (11) shows "This day is past."; nothing was added for it.
- Past dates: the planning period may still be set wholly before today, and stays shown; it was left as is, as no entry names it.
- Schedule display: Set note now drops the leading and trailing spaces and line breaks, but notes saved before keep theirs, so one of only spaces still shows blank on My availability, where `/planning/ui/my-availability/none` gives "None" only to an empty note (the code already shows "None" for it); a migration trimming the stored notes is the human's call.
- Schedule display: the note icon is named "Note", the note being its description, rather than the note itself; the absence icon keeps its text as its name, as it is short.
- Schedule display: the menu opens at once with its title and a loading sign, the rest coming with the server's answer; an answer for an earlier click, or after the menu closed, is dropped. A closure's day on a weekday with no slot gets no column of its own, as it removes no opening.
- Schedule display: no operation of `docs/` names what the Occurrence menu loads (members, counts, absences, notes), a gap older than this feature; the menu's loading and its outcomes are stated on the Schedule's menu action alone (`/planning/ui/schedule/load`).
- Schedule display: the third [soundness] check of the menu's loading reported three points (a menu reopened on the same occurrence, when the past date is judged, and a load that fails never "loading"); `[opens]`, `[latest]` and `[load]` of `/planning/ui/schedule` were then rewritten per click, the past date judged when the load ends, which no check has re-read.
- Taken occurrences: a manager may give an occurrence away from a confirmed registration too, cancelling a member's commitment behind a confirmation; the member is not told, as the software sends no notice of registrations, and sees their name struck only on the Schedule (Get schedule shows the new registration, not the cancelled one); limiting it to proposed registrations, or telling the member, is the human's call.
- Taken occurrences: the move reuses Register with an optional `replacing`, so the cancellation and the new registration happen in one operation; a `replacing` that is no longer the occurrence's registration is refused as taken when another holds it, and registers normally when the occurrence has become free.
- Taken occurrences: `design/occurrence-menu.md` shows no refused state of the move's confirmation ("Someone took this slot in the meantime.", "This day is past."), as for Cancel registration's; whether they need a mockup is left to the human.
- Clipboard: when the browser refuses the clipboard, Copy says "The link couldn't be copied. Select it to copy it." in place of "Link copied.", the link staying shown in full for the user to copy by hand; the page does not select it for them, and which message stays after two Copies whose answers cross is left free.
- Years on dates: every date of My associations now shows its year, as Schedule settings and My availability already do, a period writing a year it shares once ("2–25 Nov 2026"); showing the year only outside the current year, a lighter summary but a second rule, is the human's call.
- Years on dates: the Occurrence menu's title ("Thu 29 Oct · 10–13") and the Schedule's day headings still show no year, as their weeks sit under the Schedule's dated Today and planning lines; and Schedule settings writes the period in full ("Mon 2 Nov 2026 – Wed 25 Nov 2026") where My associations shortens it; both left as is.
- Dialogs: a single reset when a dialog opens (a shared macro or a `toggle` listener), rather than one per opener, would stop an opener from forgetting it (six did); a backlog candidate.
- Process: when a change removes an element a screen shows, search the tests by its visible text too, not only by cited paths (the e2e test of New association still waited for its heading); no plugin change.
- Access pages: the e2e tests leave four gaps, a test-hardening candidate: the [Try again] button hidden while the action runs, and the running text back after [Try again]; [Try again] failing again on Confirm email (only Access link has it); a failure by network abort, not only a 500; and `getByText('My associations')` unscoped in the Confirm email test.
- Access pages: an action that runs on opening (`data-init`) needs the same `$_failed` handling as a dialog opener; the layout's `after_error` block serves [Try again] today, and a shared failure-with-retry component, rather than one per page, is a backlog candidate.
- Process: a suggested change of the Dev43 plugin (project gilda, increment polish-access-pages, Dev43 4.6.0): in an ungated Tests phase, run the [faithful] and [cases] agent checks before the Tests exit commit, as tests are read-only after it; otherwise their findings arrive when only a return can fix them.
- Sign-in links: `User.access_link` is loaded on every user load for the header menu; lazy loading only on pages rendering the menu is a possible refinement.
