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

- [create] A button, "+" then its name, opens a form to create, in a
  dialog or on its own page; with nothing to enter, it creates at
  once.
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
- [managers] Only managers see the buttons and icons that create, edit
  or delete an association's data; a member's own data, on My
  availability, has them for every member.

## Errors

- [generic] An operation refused or failing, on the server or on the
  way to it, where the screen names no message for it: "Something went
  wrong. Try again." on its screen.
- [kept] What was typed stays.
