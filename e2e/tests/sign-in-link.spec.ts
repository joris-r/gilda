import { expect, test, type APIRequestContext } from '@playwright/test'
import { createAccount, latestToken, uniqueEmail, datastarReady } from './helpers'

const GENERIC = 'Something went wrong. Try again.'
const LINK_INVALID = 'This link is no longer valid.'

/** Creates a confirmed account for `email`, asks for its sign-in link, and returns its token. */
async function askForLink(request: APIRequestContext, email: string) {
  await createAccount(request, 'Alice', email)
  const confirmation = await latestToken(email)
  await request.post('/sign-in-link', { data: { email } })
  await expect.poll(() => latestToken(email)).not.toBe(confirmation)
  return latestToken(email)
}

test.describe('Sign-in link', () => {
  // /core/ui/sign-in/link
  // /core/ui/sign-in-link/form
  test('Sign in leads to it, and it leads back to Sign in', async ({ page }) => {
    await page.goto('/')
    await datastarReady(page)

    await page.getByRole('link', { name: 'Sign in with an email link' }).click()
    await expect(page.getByRole('heading', { name: 'Sign in with an email link' })).toBeVisible()
    await datastarReady(page)

    await page.getByRole('link', { name: 'Back to Sign in' }).click()
    await expect(page.getByRole('button', { name: 'Sign in' })).toBeVisible()
  })

  // /core/ui/sign-in-link/send
  test('submitting replaces the form with the message', async ({ page }) => {
    const email = uniqueEmail('Nobody')
    await page.goto('/sign-in-link')
    await datastarReady(page)

    await page.getByLabel('Email', { exact: true }).fill(email)
    await page.getByRole('button', { name: 'Send me a link' }).click()

    await expect(
      page.getByText(`If ${email} is known here, a sign-in link has been sent to it.`),
    ).toBeVisible()
    await expect(page.getByRole('button', { name: 'Send me a link' })).toBeHidden()
    await expect(page.getByRole('link', { name: 'Back to Sign in' })).toBeVisible()
  })

  // /core/operations/general/malformed
  test('the browser refuses an invalid email', async ({ page }) => {
    await page.goto('/sign-in-link')
    await datastarReady(page)

    await page.getByLabel('Email', { exact: true }).fill('not-an-email')
    await page.getByRole('button', { name: 'Send me a link' }).click()

    await expect(page.getByRole('button', { name: 'Send me a link' })).toBeVisible()
    await expect(page.getByText('is known here')).toBeHidden()
  })

  // /ui/errors/generic
  // /ui/errors/kept
  test('when the server fails: the generic error message, and what was typed stays', async ({
    page,
  }) => {
    const email = uniqueEmail('Alice')
    await page.route('**/sign-in-link', (route) =>
      route.request().method() === 'POST'
        ? route.fulfill({ status: 500, body: 'failure' })
        : route.continue(),
    )
    await page.goto('/sign-in-link')
    await datastarReady(page)

    await page.getByLabel('Email', { exact: true }).fill(email)
    await page.getByRole('button', { name: 'Send me a link' }).click()

    await expect(page.getByText(GENERIC)).toBeVisible()
    await expect(page.getByLabel('Email', { exact: true })).toHaveValue(email)
  })
})

test.describe('Access link', () => {
  // /core/ui/access-link/signed-in
  // /core/operations/sign-in-by-access-link/signed-in
  test('the link leads to My associations, signed in, and stays usable', async ({
    page,
    request,
  }) => {
    const token = await askForLink(request, uniqueEmail('Alice'))

    await page.goto(`/access?token=${token}`)
    await datastarReady(page)

    await expect(page.locator('header').getByText('My associations')).toBeVisible()
    await expect(page).toHaveURL(/\/$/)
    await datastarReady(page)

    await page.locator('header').getByRole('button', { name: 'Alice' }).click()
    await page.getByRole('button', { name: 'Sign out' }).click()
    await expect(page.getByRole('button', { name: 'Sign in' })).toBeVisible()

    await page.goto(`/access?token=${token}`)
    await datastarReady(page)

    await expect(page.locator('header').getByText('My associations')).toBeVisible()
  })

  // /core/ui/access-link/invalid
  test('an unknown link shows the message and a way to Sign-in link', async ({ page }) => {
    await page.goto('/access?token=unknown-token')
    await datastarReady(page)

    await expect(page.getByText(LINK_INVALID)).toBeVisible()

    await page.getByRole('link', { name: 'Request a new link' }).click()
    await expect(page.getByRole('heading', { name: 'Sign in with an email link' })).toBeVisible()
  })

  // /core/ui/access-link/running
  test('while it runs: only "Signing you in…" under the header', async ({ page }) => {
    await page.route('**/access*', async (route) => {
      if (route.request().method() !== 'POST') return route.continue()
      await new Promise((resolve) => setTimeout(resolve, 1500))
      return route.continue()
    })

    await page.goto('/access?token=unknown-token')
    await datastarReady(page)

    await expect(page.getByText('Signing you in…')).toBeVisible()
    await expect(page.getByText(LINK_INVALID)).toBeHidden()
    await expect(page.getByText(GENERIC)).toBeHidden()
    await expect(page.getByText(LINK_INVALID)).toBeVisible()
    await expect(page.getByText('Signing you in…')).toBeHidden()
  })

  // /core/ui/access-link/failed
  // /ui/errors/generic
  test('when the server fails: the generic error and Try again, which runs it again', async ({
    page,
    request,
  }) => {
    const token = await askForLink(request, uniqueEmail('Alice'))
    let failing = true
    let sends = 0
    await page.route('**/access*', (route) => {
      if (route.request().method() !== 'POST') return route.continue()
      sends += 1
      return failing ? route.fulfill({ status: 500, body: 'failure' }) : route.continue()
    })

    await page.goto(`/access?token=${token}`)
    await datastarReady(page)

    await expect(page.getByText(GENERIC)).toBeVisible()
    await expect(page.getByText('Signing you in…')).toBeHidden()
    expect(sends).toBe(1)

    failing = false
    await page.getByRole('button', { name: 'Try again' }).click()

    await expect(page.locator('header').getByText('My associations')).toBeVisible()
    expect(sends).toBe(2)
  })

  // /core/ui/access-link/failed
  test('Try again, failing again: the error shows again, with Try again', async ({ page }) => {
    await page.route('**/access*', (route) =>
      route.request().method() === 'POST'
        ? route.fulfill({ status: 500, body: 'failure' })
        : route.continue(),
    )
    await page.goto('/access?token=unknown-token')
    await datastarReady(page)
    await expect(page.getByRole('button', { name: 'Try again' })).toBeVisible()

    await page.getByRole('button', { name: 'Try again' }).click()

    await expect(page.getByText(GENERIC)).toBeVisible()
    await expect(page.getByRole('button', { name: 'Try again' })).toBeVisible()
  })
})
