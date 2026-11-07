import { expect, test, type APIRequestContext, type Locator, type Page } from '@playwright/test'
import { PASSWORD, latestToken, uniqueEmail } from './helpers'

const GENERIC = 'Something went wrong. Try again.'
const LAST_MANAGER = 'An association keeps at least one manager.'
const REMOVE_CHLOE =
  'Remove Chloé from the association? Their upcoming registrations are cancelled.'

/**
 * Alice signs in on `page`, creates an association, adds Chloé as volunteer (and the
 * `others`), then opens its Members; returns Chloé's email.
 */
async function openMembers(
  page: Page,
  request: APIRequestContext,
  others: [string, string][] = [],
) {
  const alice = uniqueEmail('Alice')
  await request.post('/signup', { data: { displayName: 'Alice', email: alice, password: PASSWORD } })
  await request.post('/verify-email', { data: { token: await latestToken(alice) } })
  await page.goto('/')
  await page.getByLabel('Email', { exact: true }).fill(alice)
  await page.getByLabel('Password', { exact: true }).fill(PASSWORD)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page.locator('header').getByText('My associations')).toBeVisible()
  const slug = `e2e-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
  const created = await page.request.post('/api/associations', {
    data: { name: 'Jardin partagé', slug },
  })
  expect(created.status()).toBe(201)
  const { id } = (await created.json()) as { id: string }
  const chloe = uniqueEmail('Chloe')
  for (const [displayName, role] of [['Chloé', 'volunteer'], ...others]) {
    const email = displayName === 'Chloé' ? chloe : uniqueEmail('Other')
    const added = await page.request.post(`/api/associations/${id}/members`, {
      data: { display_name: displayName, email, role },
    })
    expect(added.status()).toBe(201)
  }
  await page.goto(`/association/${slug}/members`)
  await expect(page.locator('header').getByText('Members')).toBeVisible()
  return chloe
}

/** Opens the edit dialog of `displayName` and returns it. */
async function openEdit(page: Page, displayName: string) {
  await page.getByRole('button', { name: `Edit ${displayName}`, exact: true }).click()
  const dialog = page.getByRole('dialog', { name: displayName, exact: true })
  await expect(dialog).toBeVisible()
  return dialog
}

function line(page: Page, text: string) {
  return page.locator('main').getByRole('listitem').filter({ hasText: text })
}

function role(dialog: Locator) {
  return dialog.getByRole('combobox', { name: /^Role/ })
}

/** Opens the confirmation of "Remove from the association" from the edit dialog of `displayName`. */
async function askToRemove(page: Page, displayName: string, question: string) {
  const dialog = await openEdit(page, displayName)
  await dialog.getByRole('button', { name: 'Remove from the association' }).click()
  const confirmation = page.getByRole('dialog', { name: question, exact: true })
  await expect(confirmation).toBeVisible()
  return confirmation
}

test.describe('Members: the edit dialog', () => {
  test('the edit icon opens it, with the email, the role and its actions', async ({ page, request }) => {
    const chloe = await openMembers(page, request)

    const dialog = await openEdit(page, 'Chloé')

    await expect(dialog).toContainText(chloe)
    await expect(role(dialog)).toHaveValue('volunteer')
    await expect(dialog.getByRole('button', { name: 'Save' })).toBeVisible()
    await expect(dialog.getByRole('button', { name: 'Cancel' })).toBeVisible()
    await expect(dialog.getByRole('button', { name: 'Close' })).toBeVisible()
    await expect(dialog.getByRole('button', { name: 'Remove from the association' })).toBeVisible()
    await expect(dialog).not.toContainText(/sign-in link/i)
  })

  test("a manager's dialog shows Manager", async ({ page, request }) => {
    await openMembers(page, request)

    await expect(role(await openEdit(page, 'Alice'))).toHaveValue('manager')
  })

  for (const way of ['Cancel', 'the close button', 'Escape']) {
    test(`${way} closes it, changing nothing`, async ({ page, request }) => {
      await openMembers(page, request)
      const dialog = await openEdit(page, 'Chloé')
      await role(dialog).selectOption({ label: 'Manager' })

      if (way === 'Cancel') await dialog.getByRole('button', { name: 'Cancel' }).click()
      else if (way === 'Escape') await page.keyboard.press('Escape')
      else await dialog.getByRole('button', { name: 'Close' }).click()

      await expect(dialog).toBeHidden()
      await page.reload()
      await expect(line(page, 'Chloé')).toContainText(/volunteer/i)
    })
  }

  test('reopened after a Cancel, it shows the role again', async ({ page, request }) => {
    await openMembers(page, request)
    const dialog = await openEdit(page, 'Chloé')
    await role(dialog).selectOption({ label: 'Manager' })
    await dialog.getByRole('button', { name: 'Cancel' }).click()

    await expect(role(await openEdit(page, 'Chloé'))).toHaveValue('volunteer')
  })
})

test.describe('Members: changing the role', () => {
  test('Save with another role closes the dialog, says so and shows the role', async ({ page, request }) => {
    await openMembers(page, request)

    const dialog = await openEdit(page, 'Chloé')
    await role(dialog).selectOption({ label: 'Manager' })
    await dialog.getByRole('button', { name: 'Save' }).click()

    await expect(dialog).toBeHidden()
    await expect(page.getByText('Chloé is now manager.')).toBeVisible()
    await expect(line(page, 'Chloé')).toContainText(/manager/i)
    await expect(role(await openEdit(page, 'Chloé'))).toHaveValue('manager')
  })

  test('Save with the same role closes the dialog and says nothing', async ({ page, request }) => {
    await openMembers(page, request)

    const dialog = await openEdit(page, 'Chloé')
    await dialog.getByRole('button', { name: 'Save' }).click()

    await expect(dialog).toBeHidden()
    await expect(page.getByText(/is now/)).toHaveCount(0)
    await expect(line(page, 'Chloé')).toContainText(/volunteer/i)
  })

  test('demoting the last manager: the dialog stays open, with its message', async ({ page, request }) => {
    await openMembers(page, request)

    const dialog = await openEdit(page, 'Alice')
    await role(dialog).selectOption({ label: 'Volunteer' })
    await dialog.getByRole('button', { name: 'Save' }).click()

    await expect(dialog.getByText(LAST_MANAGER)).toBeVisible()
    await expect(dialog).toBeVisible()
    await page.reload()
    await expect(line(page, 'Alice')).toContainText(/manager/i)
  })

  test('when the server fails: the generic error in the dialog', async ({ page, request }) => {
    await openMembers(page, request)
    await page.route('**/role', (route) => route.fulfill({ status: 500, body: 'failure' }))

    const dialog = await openEdit(page, 'Chloé')
    await role(dialog).selectOption({ label: 'Manager' })
    await dialog.getByRole('button', { name: 'Save' }).click()

    await expect(dialog.getByText(GENERIC)).toBeVisible()
    await expect(role(dialog)).toHaveValue('manager')
  })
})

test.describe('Members: Remove from the association', () => {
  test('confirming removes the member and says so', async ({ page, request }) => {
    await openMembers(page, request)

    const confirmation = await askToRemove(page, 'Chloé', REMOVE_CHLOE)
    await confirmation.getByRole('button', { name: 'Remove' }).click()

    await expect(page.getByText('Chloé is removed.')).toBeVisible()
    await expect(page.getByRole('dialog')).toHaveCount(0)
    await expect(line(page, 'Chloé')).toHaveCount(0)
    await page.reload()
    await expect(line(page, 'Chloé')).toHaveCount(0)
  })

  test('Cancel of the confirmation changes nothing', async ({ page, request }) => {
    await openMembers(page, request)

    const confirmation = await askToRemove(page, 'Chloé', REMOVE_CHLOE)
    await confirmation.getByRole('button', { name: 'Cancel' }).click()

    await expect(confirmation).toBeHidden()
    await page.reload()
    await expect(line(page, 'Chloé')).toBeVisible()
  })

  test('removing the last manager says so and changes nothing', async ({ page, request }) => {
    await openMembers(page, request)

    const confirmation = await askToRemove(
      page,
      'Alice',
      'Remove Alice from the association? Their upcoming registrations are cancelled.',
    )
    await confirmation.getByRole('button', { name: 'Remove' }).click()

    await expect(page.getByText(LAST_MANAGER).filter({ visible: true })).toBeVisible()
    await page.reload()
    await expect(line(page, 'Alice')).toContainText(/manager/i)
  })

  test('a manager who removes themself is led to My associations', async ({ page, request }) => {
    await openMembers(page, request, [['Zoé', 'manager']])

    const confirmation = await askToRemove(
      page,
      'Alice',
      'Remove Alice from the association? Their upcoming registrations are cancelled.',
    )
    await confirmation.getByRole('button', { name: 'Remove' }).click()

    await expect(page).toHaveURL(/\/$/)
    await expect(page.locator('header').getByText('My associations')).toBeVisible()
    await expect(page.locator('main')).not.toContainText('Jardin partagé')
  })

  test('when the server fails: the generic error in the confirmation', async ({ page, request }) => {
    await openMembers(page, request)
    await page.route('**/remove', (route) => route.abort())

    const confirmation = await askToRemove(page, 'Chloé', REMOVE_CHLOE)
    await confirmation.getByRole('button', { name: 'Remove' }).click()

    await expect(confirmation.getByText(GENERIC)).toBeVisible()
    await expect(confirmation).toContainText(REMOVE_CHLOE)
  })
})
