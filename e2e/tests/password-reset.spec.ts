import { expect, test, type APIRequestContext, type Page } from '@playwright/test'
import { PASSWORD, createAccount, latestToken, uniqueEmail } from './helpers'

const GENERIC = 'Something went wrong. Try again.'
const LINK_INVALID = 'This link is no longer valid.'
const NEW_PASSWORD = 'battery staple'

/** Creates a confirmed account for `email`, asks for a reset link, and returns its token. */
async function askForResetLink(request: APIRequestContext, email: string) {
  await createAccount(request, 'Alice', email)
  const confirmation = await latestToken(email)
  await request.post('/forgot-password', { data: { email } })
  await expect.poll(() => latestToken(email)).not.toBe(confirmation)
  return latestToken(email)
}

async function submitNewPassword(page: Page, password: string) {
  await page.getByLabel('New password', { exact: true }).fill(password)
  await page.getByRole('button', { name: 'Set password' }).click()
}

test.describe('Forgot password', () => {
  test('Sign in leads to it, and it leads back to Sign in', async ({ page }) => {
    await page.goto('/')

    await page.getByRole('link', { name: 'Forgot your password?' }).click()
    await expect(page.getByRole('heading', { name: 'Forgot your password?' })).toBeVisible()

    await page.getByRole('link', { name: 'Back to Sign in' }).click()
    await expect(page.getByRole('button', { name: 'Sign in' })).toBeVisible()
  })

  test('submitting replaces the form with the message', async ({ page }) => {
    const email = uniqueEmail('Nobody')
    await page.goto('/forgot-password')

    await page.getByLabel('Email', { exact: true }).fill(email)
    await page.getByRole('button', { name: 'Send a reset link' }).click()

    await expect(
      page.getByText(`If ${email} has an account, a reset link has been sent to it.`),
    ).toBeVisible()
    await expect(page.getByRole('button', { name: 'Send a reset link' })).toBeHidden()
  })

  test('when the server fails: the generic error message, and what was typed stays', async ({
    page,
  }) => {
    const email = uniqueEmail('Alice')
    await page.route('**/forgot-password', (route) =>
      route.request().method() === 'POST'
        ? route.fulfill({ status: 500, body: 'failure' })
        : route.continue(),
    )
    await page.goto('/forgot-password')

    await page.getByLabel('Email', { exact: true }).fill(email)
    await page.getByRole('button', { name: 'Send a reset link' }).click()

    await expect(page.getByText(GENERIC)).toBeVisible()
    await expect(page.getByLabel('Email', { exact: true })).toHaveValue(email)
  })
})

test.describe('Reset password', () => {
  test('R22: the link leads to My associations, signed in, with the new password', async ({
    page,
    request,
  }) => {
    const email = uniqueEmail('Alice')
    const token = await askForResetLink(request, email)

    await page.goto(`/reset-password?token=${token}`)
    await submitNewPassword(page, NEW_PASSWORD)

    await expect(page.getByText('My associations')).toBeVisible()
    await expect(page).toHaveURL(/\/$/)

    await page.locator('header').getByRole('button', { name: 'Alice' }).click()
    await page.getByRole('button', { name: 'Sign out' }).click()
    await page.getByLabel('Email', { exact: true }).fill(email)
    await page.getByLabel('Password', { exact: true }).fill(PASSWORD)
    await page.getByRole('button', { name: 'Sign in' }).click()
    await expect(page.getByText('Wrong email or password.')).toBeVisible()
    await page.getByLabel('Password', { exact: true }).fill(NEW_PASSWORD)
    await page.getByRole('button', { name: 'Sign in' }).click()
    await expect(page.getByText('My associations')).toBeVisible()
  })

  test('an invalid link, when the page opens, shows the message and a way to Forgot password', async ({
    page,
  }) => {
    await page.goto('/reset-password?token=unknown-token')

    await expect(page.getByText(LINK_INVALID)).toBeVisible()
    await expect(page.getByRole('button', { name: 'Set password' })).toBeHidden()

    await page.getByRole('link', { name: 'Request a new link' }).click()
    await expect(page.getByRole('heading', { name: 'Forgot your password?' })).toBeVisible()
  })

  test('a link used up while the page is open, on submit, shows the message in place of the form', async ({
    page,
    request,
  }) => {
    const email = uniqueEmail('Alice')
    const token = await askForResetLink(request, email)
    await page.goto(`/reset-password?token=${token}`)
    await request.post('/reset-password', { data: { token, password: 'another password' } })

    await submitNewPassword(page, NEW_PASSWORD)

    await expect(page.getByText(LINK_INVALID)).toBeVisible()
    await expect(page.getByRole('button', { name: 'Set password' })).toBeHidden()

    await page.getByRole('link', { name: 'Request a new link' }).click()
    await expect(page.getByRole('heading', { name: 'Forgot your password?' })).toBeVisible()
  })

  test('the browser refuses a password of fewer than 8 characters', async ({ page, request }) => {
    const token = await askForResetLink(request, uniqueEmail('Alice'))
    await page.goto(`/reset-password?token=${token}`)

    await submitNewPassword(page, '1234567')

    await expect(page.getByRole('button', { name: 'Set password' })).toBeVisible()
    await expect(page.getByText('My associations')).toBeHidden()
  })

  test('when the server fails: the generic error message, and what was typed stays', async ({
    page,
    request,
  }) => {
    const token = await askForResetLink(request, uniqueEmail('Alice'))
    await page.route('**/reset-password', (route) =>
      route.request().method() === 'POST'
        ? route.fulfill({ status: 500, body: 'failure' })
        : route.continue(),
    )
    await page.goto(`/reset-password?token=${token}`)

    await submitNewPassword(page, NEW_PASSWORD)

    await expect(page.getByText(GENERIC)).toBeVisible()
    await expect(page.getByLabel('New password', { exact: true })).toHaveValue(NEW_PASSWORD)
  })
})
