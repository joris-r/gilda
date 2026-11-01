# Frontend refactors

ScheduleView is split into a week grid component and an occurrence menu
component, and the header logo and the favicon share one file; the
specified behavior is unchanged.

## Technical

- The header logo is `frontend/public/favicon.svg`, shown as an image.
- In dark mode, the favicon's dot takes the dark accent colour, as the
  header logo's dot does.
