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
   /planning/ui/my-availability.
   - My preferences: when saving fails, the selector keeps the value chosen though it was not saved.
   - Members' preferences: when saving fails, the selector keeps the value chosen though it was not saved, as in My preferences.
3. Confirmation error: /ui/forms.
   - Confirmation: the generic error probably still shows after Cancel and reopening, until the next try.
4. Sign-in links:
   - Revoke my sign-in link: the menu offers it to a user who has no link, and then says "revoked"; consider showing it only when they have one.
   - Sign-in link: when the email can't be sent, the link is still created, so the member later shows "Revoke link" for a link nobody received.
   - Send link drops the link when the email can't be sent, but Sign-in link keeps it; align the two.
   - Revoke link from a page opened before the member's link was revoked elsewhere still says "revoked".
5. Access pages:
   - Access link and Confirm email: the page stays blank while the action runs, and after a server failure only the generic error shows, with no way forward.
6. New association:
   - New association: its mockup shows a title in the page, but `interface.md` says the header's location stands for the title; the page follows the mockup.
   - New association: "+ New association" is a link, while `interface.md` describes a button.
7. Orders:
   - My associations: the spec sets no order, so the list follows whatever order the database returns.
   - Members: display names are ordered by `casefold`, not by the language's collation, so "Émile" comes after "Zoé".
   - Manager's menu: names are ordered by `casefold`, not by the language's collation, as on Members.
8. Stale identifiers:
   - Rename and Delete check against the name the page was loaded with: after a rename in another tab, Delete stays disabled for the new name until a reload.
   - Change the association identifier breaks every bookmark of the former URLs, with no redirect (`/core/operations/update-association/new-slug`).
   - Confirm and OK use the slug from page load, so after a change of identifier in another tab they show only the generic error.
9. Stale days:
   - Schedule: a page left open past midnight keeps the old today line and past days until it reloads.
   - Schedule: a page left open past midnight still offers Sign up on yesterday's occurrences, which then shows only the generic error.
10. Stale data:
    - Sign up: after "Someone took this slot in the meantime.", the Schedule still shows the occurrence as free until a reload.
    - Members' preferences: a member added on Members, or a choice made on My availability, shows only after a reload.
    - Shared schedule: once the link is replaced or revoked, More weeks on a page already open shows only the generic error, not "This link is no longer valid.".
    - The one-time notice is kept in the session, so it shows on whichever page loads next, even in another tab.
11. Date order messages:
    - Add a slot or Edit the slot with To not after From shows only the generic error; the former frontend said "Check the dates and times: the start comes before the end."
    - Planning period and closures with To before From show only the generic error, as Slots do.
    - Absences with To before From show only the generic error; the former frontend said "Check the dates: the start comes before the end." (its translation is gone with the former frontend's other leftovers).
12. Warnings:
    - Edit the slot and Delete the slot don't warn that the slot's registrations become obsolete, nor that deleting it deletes the members' preferences on it.
    - Add a closure, Edit the closure and Delete the closure don't warn that the registrations on the closed dates become obsolete, or stop being obsolete.
    - Closures may overlap each other, with no warning.
    - Absences may overlap each other, with no warning.
13. Past dates:
    - Closures: past closures stay listed forever; they could be listed from those ending today on, as Absences are.
    - Adding or editing an absence that ends before today saves it, but it never shows, with no message.
    - Cancel registration: the server cancels a registration dated before today (`/planning/operations/change-registration/cancel` doesn't forbid it), though no menu opens there.
14. Schedule display:
    - Schedule: a closure on a weekday with no column of the shown weeks doesn't show at all.
    - Schedule menu: it shows centred on the screen, not anchored to the occurrence.
    - Schedule menu: it opens only once the server answers, so a slow network shows nothing for a while after the click.
    - Note icon: the whole note is the icon's accessible name, so a long note gives a long screen-reader label.
    - A note of only spaces is saved as is; the Schedule's note icon (a later item) should treat it as empty.
15. Taken occurrences:
    - Manager's menu: a taken occurrence offers no names, so moving it to another member takes a cancel, then a proposal.
16. Clipboard:
    - Share link: "Link copied." shows even when the browser refuses the clipboard.
17. Years on dates:
    - My associations shows dates without their year, so a proposal months ahead (e.g. "Sun 3 Jan") is ambiguous.

## Lessons

## For the human

- Network retries: two saves of the same selector sent in quick succession (My preferences, Members' preferences) may still reach the server out of order, the older overwriting the newer; with no resend this needs a slow network and two changes within one request's time, so it is left unspecified.
- Failed saves: the outline must cite domain sections (`/planning/ui/…`) for [outline], but check.py's [depends] then reports them, as BACKLOG.md counts as the top level, which declares no domain; a false positive of the Dev43 plugin, worth an issue.
- Confirmation error: /ui/errors/kept ("What was typed stays.") does not say whether a form opened again after a failed try and Cancel keeps what was typed; /ui/forms/fresh settles only its messages, and the project backlog's Add a slot entry already touches the fields.
- Confirmation error: the Occurrence menu is not a dialog, so /ui/forms/fresh leaves open whether "Someone took this slot in the meantime." or the generic error still shows when it opens again on the same occurrence; outline item 9 or 10 may settle it.
