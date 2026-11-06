import { expect, test, type APIRequestContext, type Page } from '@playwright/test'
import { PASSWORD, latestToken, uniqueEmail } from './helpers'

/** Creates a confirmed account through the actions of the screens, and returns its email. */
async function createAccount(request: APIRequestContext, displayName: string) {
  const email = uniqueEmail(displayName)
  const created = await request.post('/signup', {
    data: { displayName, email, password: PASSWORD },
  })
  expect(created.status()).toBe(200)
  const token = await latestToken(email)
  const verified = await request.post('/verify-email', { data: { token } })
  expect(verified.status()).toBe(200)
  return email
}

async function submitSignIn(page: Page, email: string, password: string) {
  await page.getByLabel('Email', { exact: true }).fill(email)
  await page.getByLabel('Password', { exact: true }).fill(password)
  await page.getByRole('button', { name: 'Sign in' }).click()
}

test.describe('Sign in', () => {
  test('wrong credentials show the message, on the same page', async ({ page }) => {
    const email = uniqueEmail('Nobody')
    await page.goto('/')

    await submitSignIn(page, email, 'not the password')

    await expect(page.getByText('Wrong email or password.')).toBeVisible()
    await expect(page.getByLabel('Email', { exact: true })).toHaveValue(email)
  })

  test('success leads to the temporary /, and Sign out to Sign in', async ({ page, request }) => {
    const email = await createAccount(request, 'Alice')
    await page.goto('/')

    await submitSignIn(page, email, PASSWORD)

    await expect(page.getByText('My associations')).toBeVisible()
    await expect(page.getByText('Alice')).toBeVisible()

    await page.locator('header').getByRole('button', { name: 'Alice' }).click()
    await page.getByRole('button', { name: 'Sign out' }).click()

    await expect(page.getByRole('button', { name: 'Sign in' })).toBeVisible()
  })

  test('a wrong try, then the right password, signs in', async ({ page, request }) => {
    const email = await createAccount(request, 'Alice')
    await page.goto('/')

    await submitSignIn(page, email, 'not the password')
    await expect(page.getByText('Wrong email or password.')).toBeVisible()
    await submitSignIn(page, email, PASSWORD)

    await expect(page.getByText('My associations')).toBeVisible()
  })
})

test.describe('Language', () => {
  test('the language selector switches the language, and the choice is kept', async ({ page }) => {
    await page.goto('/')

    await page.getByLabel('Language').selectOption({ label: 'Français' })

    await expect(page.getByRole('button', { name: 'Se connecter' })).toBeVisible()
    await page.reload()
    await expect(page.getByRole('button', { name: 'Se connecter' })).toBeVisible()
    await expect(page.getByLabel('Langue')).toHaveValue('fr')

    await page.getByLabel('Langue').selectOption({ label: 'English' })

    await expect(page.getByRole('button', { name: 'Sign in' })).toBeVisible()
  })

  test.describe('in a browser that prefers French', () => {
    test.use({ locale: 'fr-FR' })

    test('opens in French', async ({ page }) => {
      await page.goto('/')

      await expect(page.getByRole('button', { name: 'Se connecter' })).toBeVisible()
    })

    test('the choice wins over the browser', async ({ page }) => {
      await page.goto('/')

      await page.getByLabel('Langue').selectOption({ label: 'English' })
      await expect(page.getByRole('button', { name: 'Sign in' })).toBeVisible()

      await page.reload()
      await expect(page.getByRole('button', { name: 'Sign in' })).toBeVisible()
    })
  })
})
