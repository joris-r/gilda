import { expect, test, type APIRequestContext, type Page } from '@playwright/test'
import { createAccount, latestToken, signIn, datastarReady } from './helpers'

const GENERIC = 'Something went wrong. Try again.'
const QUESTION = 'Revoke your sign-in link? Sessions opened with it are signed out.'
const REVOKED = 'Your sign-in link is revoked.'
const NONE = 'You have no sign-in link.'

/** Asks for the sign-in link of `email`, and returns its token. */
async function askForLink(request: APIRequestContext, email: string) {
  await request.post('/sign-in-link', { data: { email } })
  return latestToken(email)
}

/** Opens the session of `page` with the link. */
async function signInWithLink(page: Page, token: string) {
  await page.goto(`/access?token=${token}`)
  await datastarReady(page)
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
  const response = await request.post('/access', { data: { token } })
  return (await response.text()).includes('window.location')
}

test.describe('Header', () => {
  // /core/ui/header/title
  test('the location stands for the screen title', async ({ page, request }) => {
    await signIn(page, await createAccount(request))

    await expect(page.locator('main').getByText('My associations')).toBeHidden()
  })
})

test.describe('Header menu', () => {
  // /core/ui/header/menu
  test('offers Revoke my sign-in link only with a sign-in link', async ({ page, request }) => {
    const email = await createAccount(request)
    await signIn(page, email)
    await page.locator('header').getByRole('button', { name: 'Alice' }).click()
    await expect(page.getByRole('button', { name: 'Delete my account' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Revoke my sign-in link' })).toHaveCount(0)

    await askForLink(request, email)
    await page.reload()
    await datastarReady(page)
    await page.locator('header').getByRole('button', { name: 'Alice' }).click()

    await expect(page.getByRole('button', { name: 'Revoke my sign-in link' })).toBeVisible()
  })
})

test.describe('Revoke my sign-in link', () => {
  // /core/ui/header/revoked
  // /core/operations/revoke-my-access-link/revoked
  test('confirming closes the dialog and shows it is revoked', async ({ page, request }) => {
    const email = await createAccount(request)
    const token = await askForLink(request, email)
    await signIn(page, email)

    const dialog = await askToRevoke(page)
    await dialog.getByRole('button', { name: 'Confirm' }).click()

    await expect(page.getByText(REVOKED)).toBeVisible()
    await expect(dialog).toBeHidden()
    expect(await linkStillWorks(request, token)).toBe(false)
    await page.reload()
    await datastarReady(page)
    await expect(page.locator('header').getByText('My associations')).toBeVisible()
  })

  // /core/ui/header/this-session
  // /core/operations/revoke-my-access-link/revoked
  test('from a session opened with it, leads to Sign in', async ({ page, request }) => {
    const token = await askForLink(request, await createAccount(request))
    await signInWithLink(page, token)

    const dialog = await askToRevoke(page)
    await dialog.getByRole('button', { name: 'Confirm' }).click()

    await expect(page.getByRole('button', { name: 'Sign in' })).toBeVisible()
    expect(await linkStillWorks(request, token)).toBe(false)
  })

  // /ui/forms/cancel
  test('Cancel closes it and keeps the link', async ({ page, request }) => {
    const email = await createAccount(request)
    const token = await askForLink(request, email)
    await signIn(page, email)

    const dialog = await askToRevoke(page)
    await dialog.getByRole('button', { name: 'Cancel' }).click()

    await expect(dialog).toBeHidden()
    expect(await linkStillWorks(request, token)).toBe(true)
  })

  // /ui/forms/failure
  // /ui/errors/generic
  test('on failure, the dialog stays open with its message', async ({ page, request }) => {
    const email = await createAccount(request)
    await askForLink(request, email)
    await signIn(page, email)
    await page.route('**/revoke-access-link', (route) => route.abort())

    const dialog = await askToRevoke(page)
    await dialog.getByRole('button', { name: 'Confirm' }).click()

    await expect(dialog.getByText(GENERIC)).toBeVisible()
    await expect(dialog).toContainText(QUESTION)
  })

  // /core/ui/header/leaves
  test('after a success, the menu no longer offers it', async ({ page, request }) => {
    const email = await createAccount(request)
    await askForLink(request, email)
    await signIn(page, email)

    const dialog = await askToRevoke(page)
    await dialog.getByRole('button', { name: 'Confirm' }).click()
    await expect(dialog).toBeHidden()

    await page.locator('header').getByRole('button', { name: 'Alice' }).click()
    await expect(page.getByRole('button', { name: 'Delete my account' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Revoke my sign-in link' })).toHaveCount(0)
  })

  // /core/ui/header/none
  // /core/ui/header/leaves
  // /core/operations/revoke-my-access-link/none
  test('from a page opened before the link was revoked elsewhere, says there is none', async ({
    page,
    request,
  }) => {
    const email = await createAccount(request)
    await askForLink(request, email)
    await signIn(page, email)
    const other = await page.context().newPage()
    await other.goto('/')
    await datastarReady(other)
    const elsewhere = await askToRevoke(other)
    await elsewhere.getByRole('button', { name: 'Confirm' }).click()
    await expect(other.getByText(REVOKED)).toBeVisible()

    const dialog = await askToRevoke(page)
    await dialog.getByRole('button', { name: 'Confirm' }).click()

    await expect(page.getByText(NONE)).toBeVisible()
    await expect(page.getByText(REVOKED)).toHaveCount(0)
    await expect(dialog).toBeHidden()
    await page.locator('header').getByRole('button', { name: 'Alice' }).click()
    await expect(page.getByRole('button', { name: 'Revoke my sign-in link' })).toHaveCount(0)
  })
})
