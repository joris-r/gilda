# scenarios: the user scenarios of the end-to-end suite

A new page `spec/main/scenarios.md`, with one scenario.

## `scenarios.md` (new)

# Scenarios

## A volunteer becomes manager

1. Alice creates her account, then creates the association
   "Jardin partagé".
2. On its Association page, she adds Bruno as manager, and Chloé and
   David as volunteers. She signs out.
3. Chloé creates her account with her email. My associations shows
   Jardin partagé, VOLUNTEER. She signs out.
4. Bruno creates his account with his email, opens Jardin partagé and
   promotes Chloé: "Chloé is now manager." He signs out.
5. Chloé signs in. My associations shows Jardin partagé, MANAGER. She
   signs out.

## `technical.md`

Replaces the End-to-end item of the test and quality policy:

- End-to-end: Playwright against the running backend, frontend and
  database, one test per scenario of `scenarios.md`. Tests check text
  and behavior, never screenshots or appearance.
