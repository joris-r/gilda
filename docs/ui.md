# UI

## Not found

At any path that leads nowhere, signed in or not; mockup in
`design/not-found.md`.

- [status] It answers 404. An association screen whose slug is unknown
  is not Not found: core's Unknown association.
- [shown] "Page not found", then "Back to the home page", leading to
  `/`.
- [header] Its header is the signed-out one, signed in or not.

## Language

- [default] The interface opens in French when the browser prefers
  French, in English otherwise.
- [emails] An email the user triggers, e.g. the confirmation email, is
  in the interface's language.

## Forms

Mockup in `design/forms.md`.

- [create] "+" then its name opens a form to create: a button for a
  dialog, a link for a form on its own page; with nothing to enter, a
  button creates at once.
- [edit] An edit icon on a line opens a form to change it.
- [delete] A delete icon on a line asks for confirmation.
- [icon-names] Each icon is named by its action, e.g. "Edit the
  period", "Delete the closure".
- [dialog] A form opens in a dialog with a title, its fields, its
  submit button, Cancel and a close button.
- [close] Cancel, the close button and Escape close it, changing
  nothing.
- [success] On success, the dialog closes and the screen shows the
  result and its message, if any.
- [failure] On failure, the dialog stays open, with its message.
- [confirmation] A confirmation opens in a dialog with its question,
  its action button and Cancel, unless its screen names another
  button for Cancel.
  - [cancel] Cancel and Escape close it, changing nothing, even after
    a failed try.
  - [nested] Confirming one asked from a form's dialog also closes
    that form.
- [fresh] The message of a refused or failed try in a dialog, the
  generic error included, shows in that dialog only, until the next
  try or the dialog closes: opened again, the dialog shows none.
- [managers] Only managers see the buttons and icons that create, edit
  or delete an association's data; a member's own data, on My
  availability, has them for every member.

## Errors

- [generic] An operation refused or failing, on the server or on the
  way to it, where the screen names no message for it: "Something went
  wrong. Try again." on its screen.
- [kept] What was typed stays.
- [once] A trigger sends its operation once: after a refusal or a
  failure, on the server or on the network, nothing sends it again but
  one of its triggers firing anew: the user acting again, its page
  opening again when the page runs it on opening, or another event its
  screen names as a trigger.

## Name order

- [names] Wherever a screen sorts by name, names are sorted
  alphabetically, ignoring case and accents, e.g. "émile" and "Émile"
  before "Zoé"; between names that are equal once case and accents are
  ignored, the order is left free.

## Changed identifier

- [actions] An action on an association or its data, from a screen
  opened before the association's identifier changed, My associations
  included, acts as it would from that screen opened after the change;
  a screen of the association that the action then leads to opens at
  its current URL.
