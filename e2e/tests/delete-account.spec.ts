import { expect, test, type Page } from '@playwright/test'
import { PASSWORD, signedIn } from './helpers'

const GENERIC = 'Something went wrong. Try again.'
const QUESTION =
  'Delete your account? You leave all your associations and your upcoming registrations are cancelled. This cannot be undone.'

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
  // /core/ui/header/menu
  test('the display name opens the menu', async ({ page, request }) => {
    await signedIn(page, request)
    await expect(page.getByRole('button', { name: 'Sign out' })).toBeHidden()

    await menuButton(page).click()

    await expect(page.getByLabel('Language')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Revoke my sign-in link' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Delete my account' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Sign out' })).toBeVisible()
  })

  // /core/ui/header/language
  test('the language selector of the menu switches the language', async ({ page, request }) => {
    await signedIn(page, request)

    await menuButton(page).click()
    await page.getByLabel('Language').selectOption({ label: 'Français' })

    await expect(page.getByText('Mes associations')).toBeVisible()
  })
})

test.describe('Delete my account', () => {
  // /core/ui/header/delete
  // /core/operations/delete-account/deleted
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

  // /ui/forms/failure
  // /ui/errors/generic
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
  // /ui/forms/cancel
  test('Cancel closes it, changing nothing', async ({ page, request }) => {
    await signedIn(page, request)

    const dialog = await askToDelete(page)
    await dialog.getByRole('button', { name: 'Cancel' }).click()

    await expect(dialog).toBeHidden()
    await expectStillSignedIn(page)
  })

  // /ui/forms/cancel
  test('Escape closes it, changing nothing', async ({ page, request }) => {
    await signedIn(page, request)

    const dialog = await askToDelete(page)
    await page.keyboard.press('Escape')

    await expect(dialog).toBeHidden()
    await expectStillSignedIn(page)
  })

  // /ui/forms/cancel
  test('Cancel after a failed try changes nothing, later either', async ({ page, request }) => {
    await signedIn(page, request)
    let failed = false
    await page.route('**/delete-account', (route) => {
      if (failed) return route.continue()
      failed = true
      return route.abort()
    })

    const dialog = await askToDelete(page)
    await dialog.getByRole('button', { name: 'Delete my account' }).click()
    await expect(dialog.getByText(GENERIC)).toBeVisible()
    await dialog.getByRole('button', { name: 'Cancel' }).click()

    await page.waitForTimeout(2000) // A retry of Datastar would come after one second.
    await expectStillSignedIn(page)
  })

  // /ui/forms/confirmation
  // /core/ui/header/delete
  test('it opens again after being closed', async ({ page, request }) => {
    await signedIn(page, request)

    const dialog = await askToDelete(page)
    await dialog.getByRole('button', { name: 'Cancel' }).click()
    await expect(dialog).toBeHidden()

    await askToDelete(page)
  })
})
