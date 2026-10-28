import { defineConfig, devices } from '@playwright/test'

const PORT = 8001
const DATABASE_URL =
  process.env.DATABASE_URL ?? 'postgresql+asyncpg://gilda:gilda@localhost:5432/gilda'

export default defineConfig({
  testDir: './tests',
  reporter: [['list'], ['./slowest-reporter.ts']],
  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    command:
      'npm --prefix ../frontend run build-only && ' +
      'uv run --directory ../backend litestar --app gilda.app:create_app database upgrade --no-prompt && ' +
      `uv run --directory ../backend litestar --app gilda.app:create_app run --port ${PORT}`,
    port: PORT,
    env: { DATABASE_URL, GILDA_FRONTEND_DIR: '../frontend/dist' },
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
})
