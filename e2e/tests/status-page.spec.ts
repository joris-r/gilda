import { expect, test } from '@playwright/test'

test.describe('Status page', () => {
  test('shows the API and the database reachable', async ({ page }) => {
    await page.goto('/')

    await expect(page.getByText('Gilda status')).toBeVisible()
    await expect(page.locator('body')).toContainText(/API:\s*reachable/)
    await expect(page.locator('body')).toContainText(/Database:\s*reachable/)
  })
})

test.describe('Language selector', () => {
  test('switches to French and keeps the choice across visits', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByText('Gilda status')).toBeVisible()

    await page.getByRole('combobox').selectOption('fr')

    await expect(page.getByText('État de Gilda')).toBeVisible()
    await expect(page.locator('body')).toContainText(/API\s*:\s*accessible/)
    await expect(page.locator('body')).toContainText(/Base de données\s*:\s*accessible/)

    await page.reload()

    await expect(page.getByText('État de Gilda')).toBeVisible()
  })
})
