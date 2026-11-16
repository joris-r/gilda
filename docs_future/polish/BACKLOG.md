# Polish

Settles the defects and open choices found by the Datastar rewrite:
actions that run twice, stale pages, missing messages and warnings,
orders and displays.

## Outline

Each increment lists the sections it integrates, then the entries it
settles.

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
- Stale identifiers: every action of an association screen carries the association's id in an `X-Association` header (`headers: {'X-Association': '{{ association.id }}'}` on its `@post`; the URLs keep their slug), and its handler resolves it with `association_ref` and `detail_by_ref`; later items' new actions on an association screen must carry it, and a redirect to an association screen must use the current slug (`current_slug`).
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
- Orders: `web/ordering.py` holds `name_key`, which Members and My associations use; item 10's Manager's menu (`planning/pages.py`) uses it in place of `casefold`, with no edit of `docs/`, as `/ui/name-order/names` and `/planning/ui/occurrence-menu/order` already settle it.
- Tests: search the tests by the visible text of what a change shows, in English and French, and by the helpers that build it (e.g. `label()`, the period strings of `test_the_periods_dates`), not only by the paths they cite; this increment's first Tests phase missed that test.
- Years: My associations' registration dates now carry the year ("Thu 5 Nov 2026"), through the template helper `full_day`; the Schedule, the Occurrence menu and the other screens keep their year-less forms, which later items must not read as changed.
- Soundness: the third [soundness] check was not re-read after its fixes on Members' preferences shown again (`/planning/ui/schedule-settings/preferences-again`, rewritten to wait until no save runs, as a numbered list ending in "Otherwise") and on the menu's loading (`[opens]`, `[latest]` and `[load]` of `/planning/ui/schedule`, rewritten per click, the past date judged when the load ends); the integrating increments re-read them.
- Stale tests: the stale-screen tests are Playwright two-tab tests (`e2e/tests/changed-identifier.spec.ts`, helper `changeIdentifierElsewhere`); items 7 and 11 can reuse the pattern.
- Notices: a later action that leads to another screen with a message calls `flash` and its POST sends `X-Tab: window.gildaTab`, or the message shows on any tab-less load.
- Stale tests: a two-tab test can hold an action's answer with `page.route`, `route.fetch` and `fulfill` (`e2e/tests/notices.spec.ts`, `holdingTheAnswer`) to run something in another tab between the action and its redirect; items 8 to 11 can reuse it.
- Tests: the two test suites (`make test-backend`, `make test-e2e`) share one test database and never run at once.
- Tests: a past state (an absence that ended, a past closure or registration) cannot be reached by operations; a test moves rows into the past by SQL, as in `test_availability_screen.py`.
- Page scripts: a script of a screen goes in a static file (`web/static/availability.js`), not inline, as the tests read the text of the sections of `main`.
- Tests: in Playwright, the generic error within a dialog is counted with `filter({ visible: true })`, as each dialog holds a hidden copy.
- Members' preferences (item 9): its selector needs the logic of `web/static/availability.js` (the value shown while a save runs, then the value of the save answered last), and item 9's closure and period checks can follow `_check_absence_dates` of `planning/services.py`.
- Shown again (item 9): a refresh after the screen was hidden is a plain GET answering a fragment with status codes (401 leads to Sign in, any other failure is silent), by `web/static/settings.js`, which waits for no running save and fetches again if a save began meanwhile; item 11's new-day refresh can reuse the pattern.
- Tests: Playwright simulates a screen hidden then shown by overriding `document.hidden` and `visibilityState` and dispatching `visibilitychange` (`hideThenShow` in `schedule-settings.spec.ts`).
- Dialogs: a confirmation's accessible name is its question, so text appended to a question (the warnings) changes it; e2e helpers match it without `exact`, and items 10 and 11 should expect the same.
- Share link: Copy's status is one `data-text` signal holding the message, as a second hidden paragraph would break `toHaveCount(0)` checks; a `data-on` expression holds no `>` (no arrow function, use `function () {}`), as page tests strip tags with `<[^>]+>`.
