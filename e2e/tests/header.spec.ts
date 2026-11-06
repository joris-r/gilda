import { expect, test, type APIRequestContext, type Page } from '@playwright/test'
import { PASSWORD, latestToken, uniqueEmail } from './helpers'

const GENERIC = 'Something went wrong. Try again.'
const QUESTION = 'Revoke your sign-in link? Sessions opened with it are signed out.'
const REVOKED = 'Your sign-in link is revoked.'

async function createAccount(request: APIRequestContext) {
  const email = uniqueEmail('Alice')
  await request.post('/signup', { data: { displayName: 'Alice', email, password: PASSWORD } })
  await request.post('/verify-email', { data: { token: await latestToken(email) } })
  return email
}

async function signInWithPassword(page: Page, email: string) {
  await page.goto('/')
  await page.getByLabel('Email', { exact: true }).fill(email)
  await page.getByLabel('Password', { exact: true }).fill(PASSWORD)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page.locator('header').getByText('My associations')).toBeVisible()
}

/** Asks for the sign-in link of `email`, and returns its token. */
async function askForLink(request: APIRequestContext, email: string) {
  await request.post('/api/access-link', { data: { email } })
  return latestToken(email)
}

/** Opens the session of `page` with the link: its screen is not served yet. */
async function signInWithLink(page: Page, token: string) {
  await page.request.post('/api/session/access-link', { data: { token } })
  await page.goto('/')
  await expect(page.locator('header').getByText('My associations')).toBeVisible()
}

/** Opens the menu, then the confirmation of "Revoke my sign-in link", and returns its dialog. */
async function askToRevoke(page: Page) {
  await page.locator('header').getByRole('button', { name: 'Alice' }).click()
  await page.getByRole('button', { name: 'Revoke my sign-in link' }).click()
  const dialog = page.getByRole('dialog')
  await expect(dialog).toContainText(QUESTION)
  return dialog
}

async function linkStillWorks(request: APIRequestContext, token: string) {
  const response = await request.post('/api/session/access-link', { data: { token } })
  return response.status() === 200
}

test.describe('Header', () => {
  test('the location stands for the screen title', async ({ page, request }) => {
    await signInWithPassword(page, await createAccount(request))

    await expect(page.locator('main').getByText('My associations')).toBeHidden()
  })
})

test.describe('Revoke my sign-in link', () => {
  test('confirming closes the dialog and shows it is revoked', async ({ page, request }) => {
    const email = await createAccount(request)
    const token = await askForLink(request, email)
    await signInWithPassword(page, email)

    const dialog = await askToRevoke(page)
    await dialog.getByRole('button', { name: 'Confirm' }).click()

    await expect(page.getByText(REVOKED)).toBeVisible()
    await expect(dialog).toBeHidden()
    expect(await linkStillWorks(request, token)).toBe(false)
    await page.reload()
    await expect(page.locator('header').getByText('My associations')).toBeVisible()
  })

  test('from a session opened with it, leads to Sign in', async ({ page, request }) => {
    const token = await askForLink(request, await createAccount(request))
    await signInWithLink(page, token)

    const dialog = await askToRevoke(page)
    await dialog.getByRole('button', { name: 'Confirm' }).click()

    await expect(page.getByRole('button', { name: 'Sign in' })).toBeVisible()
    expect(await linkStillWorks(request, token)).toBe(false)
  })

  test('Cancel closes it and keeps the link', async ({ page, request }) => {
    const email = await createAccount(request)
    const token = await askForLink(request, email)
    await signInWithPassword(page, email)

    const dialog = await askToRevoke(page)
    await dialog.getByRole('button', { name: 'Cancel' }).click()

    await expect(dialog).toBeHidden()
    expect(await linkStillWorks(request, token)).toBe(true)
  })

  test('on failure, the dialog stays open with its message', async ({ page, request }) => {
    await signInWithPassword(page, await createAccount(request))
    await page.route('**/revoke-access-link', (route) => route.abort())

    const dialog = await askToRevoke(page)
    await dialog.getByRole('button', { name: 'Confirm' }).click()

    await expect(dialog.getByText(GENERIC)).toBeVisible()
    await expect(dialog).toContainText(QUESTION)
  })

  test('it can be confirmed again, after a success', async ({ page, request }) => {
    await signInWithPassword(page, await createAccount(request))

    const dialog = await askToRevoke(page)
    await dialog.getByRole('button', { name: 'Confirm' }).click()
    await expect(dialog).toBeHidden()

    const again = await askToRevoke(page)
    await again.getByRole('button', { name: 'Confirm' }).click()

    await expect(again).toBeHidden()
    await expect(page.getByText(REVOKED)).toBeVisible()
  })
})
