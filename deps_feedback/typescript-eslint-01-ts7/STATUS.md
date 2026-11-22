# Status

- **Upstream:** not reported by us; typescript-eslint already states it
  requires `typescript >=4.8.4 <6.1.0`, and TypeScript 7 ships no JS API.
- **In the project:** `e2e/package.json` pins `typescript` to
  `npm:@typescript/typescript6`, so ESLint can parse the end-to-end tests.
- **Backlog:** "Return e2e to TypeScript 7 once typescript-eslint
  supports it", under `## For the human` in
  `docs_future/test-quality/BACKLOG.md`.
- **Done when:** a typescript-eslint release supports TypeScript 7 and
  e2e is back on it. Not done.
