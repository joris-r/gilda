import { expect, test, type APIRequestContext } from '@playwright/test'
import { PASSWORD, latestToken, uniqueEmail } from './helpers'

const GENERIC = 'Something went wrong. Try again.'
const LINK_INVALID = 'This link is no longer valid.'

/** Creates a confirmed account for `email`, asks for its sign-in link, and returns its token. */
async function askForLink(request: APIRequestContext, email: string) {
  await request.post('/signup', { data: { displayName: 'Alice', email, password: PASSWORD } })
  const confirmation = await latestToken(email)
  await request.post('/verify-email', { data: { token: confirmation } })
  await request.post('/sign-in-link', { data: { email } })
  await expect.poll(() => latestToken(email)).not.toBe(confirmation)
  return latestToken(email)
}

test.describe('Sign-in link', () => {
  test('Sign in leads to it, and it leads back to Sign in', async ({ page }) => {
    await page.goto('/')

    await page.getByRole('link', { name: 'Sign in with an email link' }).click()
    await expect(page.getByRole('heading', { name: 'Sign in with an email link' })).toBeVisible()

    await page.getByRole('link', { name: 'Back to Sign in' }).click()
    await expect(page.getByRole('button', { name: 'Sign in' })).toBeVisible()
  })

  test('submitting replaces the form with the message', async ({ page }) => {
    const email = uniqueEmail('Nobody')
    await page.goto('/sign-in-link')

    await page.getByLabel('Email', { exact: true }).fill(email)
    await page.getByRole('button', { name: 'Send me a link' }).click()

    await expect(
      page.getByText(`If ${email} is known here, a sign-in link has been sent to it.`),
    ).toBeVisible()
    await expect(page.getByRole('button', { name: 'Send me a link' })).toBeHidden()
    await expect(page.getByRole('link', { name: 'Back to Sign in' })).toBeVisible()
  })

  test('the browser refuses an invalid email', async ({ page }) => {
    await page.goto('/sign-in-link')

    await page.getByLabel('Email', { exact: true }).fill('not-an-email')
    await page.getByRole('button', { name: 'Send me a link' }).click()

    await expect(page.getByRole('button', { name: 'Send me a link' })).toBeVisible()
    await expect(page.getByText('is known here')).toBeHidden()
  })

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

    await page.getByLabel('Email', { exact: true }).fill(email)
    await page.getByRole('button', { name: 'Send me a link' }).click()

    await expect(page.getByText(GENERIC)).toBeVisible()
    await expect(page.getByLabel('Email', { exact: true })).toHaveValue(email)
  })
})

test.describe('Access link', () => {
  test('the link leads to My associations, signed in, and stays usable', async ({
    page,
    request,
  }) => {
    const token = await askForLink(request, uniqueEmail('Alice'))

    await page.goto(`/access?token=${token}`)

    await expect(page.locator('header').getByText('My associations')).toBeVisible()
    await expect(page).toHaveURL(/\/$/)

    await page.locator('header').getByRole('button', { name: 'Alice' }).click()
    await page.getByRole('button', { name: 'Sign out' }).click()
    await expect(page.getByRole('button', { name: 'Sign in' })).toBeVisible()

    await page.goto(`/access?token=${token}`)

    await expect(page.locator('header').getByText('My associations')).toBeVisible()
  })

  test('an unknown link shows the message and a way to Sign-in link', async ({ page }) => {
    await page.goto('/access?token=unknown-token')

    await expect(page.getByText(LINK_INVALID)).toBeVisible()

    await page.getByRole('link', { name: 'Request a new link' }).click()
    await expect(page.getByRole('heading', { name: 'Sign in with an email link' })).toBeVisible()
  })

  test('when the server fails: the generic error message', async ({ page }) => {
    await page.route('**/access*', (route) =>
      route.request().method() === 'POST'
        ? route.fulfill({ status: 500, body: 'failure' })
        : route.continue(),
    )

    await page.goto('/access?token=unknown-token')

    await expect(page.getByText(GENERIC)).toBeVisible()
  })
})
