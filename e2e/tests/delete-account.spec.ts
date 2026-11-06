import { expect, test, type APIRequestContext, type Page } from '@playwright/test'
import { PASSWORD, latestToken, uniqueEmail } from './helpers'

const GENERIC = 'Something went wrong. Try again.'
const QUESTION =
  'Delete your account? You leave all your associations and your upcoming registrations are cancelled. This cannot be undone.'

/** Creates a confirmed account, signs in on `page`, and returns its email. */
async function signedIn(page: Page, request: APIRequestContext) {
  const email = uniqueEmail('Alice')
  await request.post('/signup', { data: { displayName: 'Alice', email, password: PASSWORD } })
  await request.post('/verify-email', { data: { token: await latestToken(email) } })
  await page.goto('/')
  await page.getByLabel('Email', { exact: true }).fill(email)
  await page.getByLabel('Password', { exact: true }).fill(PASSWORD)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page.getByText('My associations')).toBeVisible()
  return email
}

function menuButton(page: Page) {
  return page.locator('header').getByRole('button', { name: 'Alice' })
}

/** Opens the menu, then the confirmation of "Delete my account", and returns its dialog. */
async function askToDelete(page: Page) {
  await menuButton(page).click()
  await page.getByRole('button', { name: 'Delete my account' }).click()
  const dialog = page.getByRole('dialog')
  await expect(dialog).toContainText(QUESTION)
  return dialog
}

async function expectStillSignedIn(page: Page) {
  await page.reload()
  await expect(page.getByText('My associations')).toBeVisible()
}

test.describe('Header', () => {
  test('the display name opens the menu', async ({ page, request }) => {
    await signedIn(page, request)
    await expect(page.getByRole('button', { name: 'Sign out' })).toBeHidden()

    await menuButton(page).click()

    await expect(page.getByLabel('Language')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Delete my account' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Sign out' })).toBeVisible()
  })

  test('the language selector of the menu switches the language', async ({ page, request }) => {
    await signedIn(page, request)

    await menuButton(page).click()
    await page.getByLabel('Language').selectOption({ label: 'Français' })

    await expect(page.getByText('Mes associations')).toBeVisible()
  })
})

test.describe('Delete my account', () => {
  test('asks for confirmation, and confirming leads to Sign in', async ({ page, request }) => {
    const email = await signedIn(page, request)

    const dialog = await askToDelete(page)
    await dialog.getByRole('button', { name: 'Delete my account' }).click()

    await expect(page.getByRole('button', { name: 'Sign in' })).toBeVisible()
    await page.getByLabel('Email', { exact: true }).fill(email)
    await page.getByLabel('Password', { exact: true }).fill(PASSWORD)
    await page.getByRole('button', { name: 'Sign in' }).click()
    await expect(page.getByText('Wrong email or password.')).toBeVisible()
  })

  test('on failure, the dialog stays open with its message', async ({ page, request }) => {
    await signedIn(page, request)
    await page.route('**/delete-account', (route) => route.abort())

    const dialog = await askToDelete(page)
    await dialog.getByRole('button', { name: 'Delete my account' }).click()

    await expect(dialog.getByText(GENERIC)).toBeVisible()
    await expect(dialog).toContainText(QUESTION)
  })
})

test.describe('Forms: a confirmation', () => {
  test('Cancel closes it, changing nothing', async ({ page, request }) => {
    await signedIn(page, request)

    const dialog = await askToDelete(page)
    await dialog.getByRole('button', { name: 'Cancel' }).click()

    await expect(dialog).toBeHidden()
    await expectStillSignedIn(page)
  })

  test('Escape closes it, changing nothing', async ({ page, request }) => {
    await signedIn(page, request)

    const dialog = await askToDelete(page)
    await page.keyboard.press('Escape')

    await expect(dialog).toBeHidden()
    await expectStillSignedIn(page)
  })

  test('it opens again after being closed', async ({ page, request }) => {
    await signedIn(page, request)

    const dialog = await askToDelete(page)
    await dialog.getByRole('button', { name: 'Cancel' }).click()
    await expect(dialog).toBeHidden()

    await askToDelete(page)
  })
})
