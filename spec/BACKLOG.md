# Backlog

- Navigation: moving between members, opening hours and the schedule is confusing; make the Schedule the association's main page, with members and opening hours as rarely used secondary pages.
- Interface: the header shows, to the right of the logo, where the user is (e.g. the association's name and the current screen), so they always know what they are looking at.
- Interface: the header shows only the user's display name and a menu at the right; Sign out and the language selector move into that menu.
- Opening hours: reverse the sections, most often changed first: Planning period, then Closures, then Slots; and rename the screen and its URL (`/opening`) to match its content.
- Association: the member list takes too much room; show only part of it, and hide the add-member form until asked for.
- Home: the "create an association" form is hidden behind an icon, opened on demand, since it is rarely used.
- Planning: the Schedule's week headings drop their date range ("Week 44 · 26 Oct – 1 Nov" becomes "Week 44").
- Planning: the schedule opens showing at least up to one week after the planning period's last date, so its end line is visible without "More weeks".
- Home: when signed in, `/` shows for each of the user's associations a summary of what concerns them: their next registration and their proposed registrations to confirm.
- Sessions: purge expired sessions regularly (Advanced Alchemy's delete_expired), so the user_session table stays small.
- Mailer: the confirmation email is English-only; send a bilingual (English/French) message instead.
- Planning: with many slots in a day, the narrow-screen Schedule becomes unusable; stack a day's slots vertically in a single column. Also check the wide screen, whose page width is capped. (3–4 slots a day, as at La Fabrique, work today.)
- Association: a manager can change the association's timezone (fixed to Europe/Paris for now).

## Security

- Session fixation: issue a new session ID at sign-in and sign-up (Litestar reuses the incoming cookie's ID).

## Quality

- Frontend: the logo path is duplicated in App.vue and favicon.svg; share one source.
