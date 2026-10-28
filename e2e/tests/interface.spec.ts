import { expect, test, type Page } from '@playwright/test'

async function signUpThroughApi(page: Page) {
  const email = `alice-${Date.now()}-${Math.random().toString(36).slice(2, 8)}@example.org`
  const response = await page.request.post('/api/accounts', {
    data: { display_name: 'Alice', email, password: 'correct horse' },
  })
  expect(response.status()).toBe(201)
}

test.describe('Interface language', () => {
  test.describe('with a French browser', () => {
    test.use({ locale: 'fr-FR' })

    test('opens in French', async ({ page }) => {
      await signUpThroughApi(page)

      await page.goto('/')

      await expect(page.getByText('Mes associations')).toBeVisible()
    })

    test('the language selector switches to English and keeps the choice', async ({ page }) => {
      await signUpThroughApi(page)
      await page.goto('/')
      await expect(page.getByText('Mes associations')).toBeVisible()

      await page.getByLabel('Langue').selectOption('en')
      await expect(page.getByText('My associations')).toBeVisible()

      await page.reload()
      await expect(page.getByText('My associations')).toBeVisible()
    })
  })

  test.describe('with an English browser', () => {
    test.use({ locale: 'en-US' })

    test('opens in English', async ({ page }) => {
      await signUpThroughApi(page)

      await page.goto('/')

      await expect(page.getByText('My associations')).toBeVisible()
    })
  })
})
