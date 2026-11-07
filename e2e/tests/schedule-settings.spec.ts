import { expect, test, type APIRequestContext, type Locator, type Page } from '@playwright/test'
import { PASSWORD, latestToken, uniqueEmail } from './helpers'

const GENERIC = 'Something went wrong. Try again.'
const EXISTS = 'This slot already exists.'
const DELETE_THURSDAY = 'Delete the slot Thursday 10:00–13:00?'

function uniqueSlug() {
  return `e2e-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

/** Alice signs in on `page`, creates an association with `slots` and opens its Schedule settings. */
async function openSettings(page: Page, request: APIRequestContext, slots: [string, string, string][] = []) {
  const alice = uniqueEmail('Alice')
  await request.post('/signup', { data: { displayName: 'Alice', email: alice, password: PASSWORD } })
  await request.post('/verify-email', { data: { token: await latestToken(alice) } })
  await page.goto('/')
  await page.getByLabel('Email', { exact: true }).fill(alice)
  await page.getByLabel('Password', { exact: true }).fill(PASSWORD)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page.locator('header').getByText('My associations')).toBeVisible()
  const slug = uniqueSlug()
  const created = await page.request.post('/api/associations', { data: { name: 'Jardin partagé', slug } })
  expect(created.status()).toBe(201)
  const { id } = (await created.json()) as { id: string }
  for (const [weekday, start, end] of slots) {
    const slot = await page.request.post(`/api/associations/${id}/slots`, { data: { weekday, start, end } })
    expect(slot.status()).toBe(201)
  }
  await page.goto(`/association/${slug}/settings`)
  await expect(page.locator('header').getByText('Schedule settings')).toBeVisible()
  return slug
}

function line(page: Page, text: string) {
  return page.locator('main').getByRole('listitem').filter({ hasText: text })
}

function day(dialog: Locator) {
  return dialog.getByRole('combobox', { name: /^Day/ })
}

function from(dialog: Locator) {
  return dialog.getByLabel('From', { exact: true })
}

function to(dialog: Locator) {
  return dialog.getByLabel('To', { exact: true })
}

async function openAdd(page: Page) {
  await page.getByRole('button', { name: 'Add a slot' }).click()
  const dialog = page.getByRole('dialog', { name: 'Add a slot' })
  await expect(dialog).toBeVisible()
  return dialog
}

/** Adds a slot through the dialog "Add a slot", and waits for it to close. */
async function addSlot(page: Page, weekday: string, start: string, end: string) {
  const dialog = await openAdd(page)
  await day(dialog).selectOption({ label: weekday })
  await from(dialog).fill(start)
  await to(dialog).fill(end)
  await dialog.getByRole('button', { name: 'Add slot' }).click()
  await expect(dialog).toBeHidden()
}

async function openEdit(page: Page, text: string) {
  await line(page, text).getByRole('button', { name: 'Edit the slot' }).click()
  const dialog = page.getByRole('dialog', { name: 'Edit the slot' })
  await expect(dialog).toBeVisible()
  return dialog
}

async function askToDelete(page: Page, text: string, question: string) {
  await line(page, text).getByRole('button', { name: 'Delete the slot' }).click()
  const confirmation = page.getByRole('dialog', { name: question, exact: true })
  await expect(confirmation).toBeVisible()
  return confirmation
}

test.describe('Schedule settings: Add a slot', () => {
  test('opens the dialog "Add a slot", with Day, From and To', async ({ page, request }) => {
    await openSettings(page, request)

    const dialog = await openAdd(page)

    await expect(day(dialog)).toBeVisible()
    await expect(from(dialog)).toBeVisible()
    await expect(to(dialog)).toBeVisible()
    await expect(dialog.getByRole('button', { name: 'Add slot' })).toBeVisible()
    await expect(dialog.getByRole('button', { name: 'Close' })).toBeVisible()
  })

  test('R17: opens with From and To at 09:00', async ({ page, request }) => {
    await openSettings(page, request)

    const dialog = await openAdd(page)

    await expect(from(dialog)).toHaveValue('09:00')
    await expect(to(dialog)).toHaveValue('09:00')
  })

  test('R17: changing From sets To to the same time', async ({ page, request }) => {
    await openSettings(page, request)
    const dialog = await openAdd(page)

    await from(dialog).fill('14:00')

    await expect(to(dialog)).toHaveValue('14:00')
  })

  test('R17: once To is changed, changing From leaves To as it is', async ({ page, request }) => {
    await openSettings(page, request)
    const dialog = await openAdd(page)

    await to(dialog).fill('12:00')
    await from(dialog).fill('10:00')

    await expect(from(dialog)).toHaveValue('10:00')
    await expect(to(dialog)).toHaveValue('12:00')
  })

  test('adding closes the dialog and shows the slot', async ({ page, request }) => {
    await openSettings(page, request, [['thursday', '10:00', '13:00']])

    await addSlot(page, 'Friday', '16:00', '19:00')

    await expect(line(page, 'Friday')).toContainText('16:00–19:00')
    await expect(line(page, 'Thursday')).toContainText('10:00–13:00')
    await page.reload()
    await expect(line(page, 'Friday')).toContainText('16:00–19:00')
  })

  test('R18: after a slot is added, the next dialog opens with its Day, and From and To at its end', async ({
    page,
    request,
  }) => {
    await openSettings(page, request)
    await addSlot(page, 'Friday', '16:00', '19:00')

    const dialog = await openAdd(page)

    await expect(day(dialog)).toHaveValue('friday')
    await expect(from(dialog)).toHaveValue('19:00')
    await expect(to(dialog)).toHaveValue('19:00')
  })

  test('R18: in the next dialog, To follows From again', async ({ page, request }) => {
    await openSettings(page, request)
    await addSlot(page, 'Friday', '09:00', '13:00')

    const dialog = await openAdd(page)
    await from(dialog).fill('15:00')

    await expect(to(dialog)).toHaveValue('15:00')
  })

  test('R18: the slot added last sets the next dialog', async ({ page, request }) => {
    await openSettings(page, request)
    await addSlot(page, 'Friday', '09:00', '13:00')
    await addSlot(page, 'Saturday', '14:00', '17:30')

    const dialog = await openAdd(page)

    await expect(day(dialog)).toHaveValue('saturday')
    await expect(from(dialog)).toHaveValue('17:30')
    await expect(to(dialog)).toHaveValue('17:30')
  })

  test('R18: after a slot is edited, Add a slot still opens as in R17', async ({ page, request }) => {
    await openSettings(page, request, [['thursday', '10:00', '13:00']])
    const edit = await openEdit(page, 'Thursday')
    await day(edit).selectOption({ label: 'Friday' })
    await edit.getByRole('button', { name: 'Save' }).click()
    await expect(edit).toBeHidden()

    const dialog = await openAdd(page)

    await expect(from(dialog)).toHaveValue('09:00')
    await expect(to(dialog)).toHaveValue('09:00')
  })

  for (const way of ['Cancel', 'the close button', 'Escape']) {
    test(`${way} closes it, changing nothing`, async ({ page, request }) => {
      await openSettings(page, request)
      const dialog = await openAdd(page)
      await day(dialog).selectOption({ label: 'Friday' })
      await from(dialog).fill('16:00')
      await to(dialog).fill('19:00')

      if (way === 'Cancel') await dialog.getByRole('button', { name: 'Cancel' }).click()
      else if (way === 'Escape') await page.keyboard.press('Escape')
      else await dialog.getByRole('button', { name: 'Close' }).click()

      await expect(dialog).toBeHidden()
      await page.reload()
      await expect(line(page, 'Friday')).toHaveCount(0)
    })
  }

  test('R17: opened again after Cancel, it opens with From and To at 09:00', async ({ page, request }) => {
    await openSettings(page, request)
    let dialog = await openAdd(page)
    await from(dialog).fill('16:00')
    await to(dialog).fill('19:00')
    await dialog.getByRole('button', { name: 'Cancel' }).click()

    dialog = await openAdd(page)

    await expect(from(dialog)).toHaveValue('09:00')
    await expect(to(dialog)).toHaveValue('09:00')
  })

  test('a slot the association already has: the dialog stays open, with its message', async ({
    page,
    request,
  }) => {
    await openSettings(page, request, [['thursday', '10:00', '13:00']])

    const dialog = await openAdd(page)
    await day(dialog).selectOption({ label: 'Thursday' })
    await from(dialog).fill('10:00')
    await to(dialog).fill('13:00')
    await dialog.getByRole('button', { name: 'Add slot' }).click()

    await expect(dialog.getByText(EXISTS)).toBeVisible()
    await expect(dialog).toBeVisible()
    await expect(from(dialog)).toHaveValue('10:00')
    await expect(line(page, 'Thursday')).toHaveCount(1)
  })

  test('when the server fails: the generic error in the dialog, and what was typed stays', async ({
    page,
    request,
  }) => {
    await openSettings(page, request)
    await page.route('**/settings/slots', (route) => route.fulfill({ status: 500, body: 'failure' }))

    const dialog = await openAdd(page)
    await day(dialog).selectOption({ label: 'Friday' })
    await from(dialog).fill('16:00')
    await to(dialog).fill('19:00')
    await dialog.getByRole('button', { name: 'Add slot' }).click()

    await expect(dialog.getByText(GENERIC)).toBeVisible()
    await expect(day(dialog)).toHaveValue('friday')
    await expect(from(dialog)).toHaveValue('16:00')
    await expect(to(dialog)).toHaveValue('19:00')
  })
})

test.describe('Schedule settings: Edit the slot', () => {
  test('opens the dialog "Edit the slot", filled with the slot', async ({ page, request }) => {
    await openSettings(page, request, [
      ['thursday', '10:00', '13:00'],
      ['saturday', '14:00', '17:30'],
    ])

    const dialog = await openEdit(page, 'Saturday')

    await expect(day(dialog)).toHaveValue('saturday')
    await expect(from(dialog)).toHaveValue('14:00')
    await expect(to(dialog)).toHaveValue('17:30')
    await expect(dialog.getByRole('button', { name: 'Save' })).toBeVisible()
    await expect(dialog.getByRole('button', { name: 'Close' })).toBeVisible()
  })

  test('changing From leaves To as it is', async ({ page, request }) => {
    await openSettings(page, request, [['thursday', '10:00', '13:00']])
    const dialog = await openEdit(page, 'Thursday')

    await from(dialog).fill('09:00')

    await expect(to(dialog)).toHaveValue('13:00')
  })

  test('Save closes the dialog and shows the slot edited', async ({ page, request }) => {
    await openSettings(page, request, [['thursday', '10:00', '13:00']])

    const dialog = await openEdit(page, 'Thursday')
    await day(dialog).selectOption({ label: 'Friday' })
    await to(dialog).fill('14:00')
    await dialog.getByRole('button', { name: 'Save' }).click()

    await expect(dialog).toBeHidden()
    await expect(line(page, 'Friday')).toContainText('10:00–14:00')
    await expect(line(page, 'Thursday')).toHaveCount(0)
    await page.reload()
    await expect(line(page, 'Friday')).toContainText('10:00–14:00')
  })

  test('opened again after a Save, it is filled with the slot edited', async ({ page, request }) => {
    await openSettings(page, request, [['thursday', '10:00', '13:00']])
    let dialog = await openEdit(page, 'Thursday')
    await to(dialog).fill('14:00')
    await dialog.getByRole('button', { name: 'Save' }).click()
    await expect(dialog).toBeHidden()

    dialog = await openEdit(page, 'Thursday')

    await expect(from(dialog)).toHaveValue('10:00')
    await expect(to(dialog)).toHaveValue('14:00')
  })

  test('as another slot of the association: the dialog stays open, with its message', async ({
    page,
    request,
  }) => {
    await openSettings(page, request, [
      ['thursday', '10:00', '13:00'],
      ['saturday', '10:00', '13:00'],
    ])

    const dialog = await openEdit(page, 'Saturday')
    await day(dialog).selectOption({ label: 'Thursday' })
    await dialog.getByRole('button', { name: 'Save' }).click()

    await expect(dialog.getByText(EXISTS)).toBeVisible()
    await expect(dialog).toBeVisible()
    await expect(line(page, 'Saturday')).toHaveCount(1)
  })

  test('Cancel closes it, changing nothing', async ({ page, request }) => {
    await openSettings(page, request, [['thursday', '10:00', '13:00']])

    const dialog = await openEdit(page, 'Thursday')
    await to(dialog).fill('14:00')
    await dialog.getByRole('button', { name: 'Cancel' }).click()

    await expect(dialog).toBeHidden()
    await page.reload()
    await expect(line(page, 'Thursday')).toContainText('10:00–13:00')
  })

  test('opened again after Cancel, it is filled with the slot', async ({ page, request }) => {
    await openSettings(page, request, [['thursday', '10:00', '13:00']])
    let dialog = await openEdit(page, 'Thursday')
    await to(dialog).fill('14:00')
    await dialog.getByRole('button', { name: 'Cancel' }).click()

    dialog = await openEdit(page, 'Thursday')

    await expect(to(dialog)).toHaveValue('13:00')
  })

  test('when the server fails: the generic error in the dialog', async ({ page, request }) => {
    await openSettings(page, request, [['thursday', '10:00', '13:00']])
    await page.route('**/edit', (route) => route.fulfill({ status: 500, body: 'failure' }))

    const dialog = await openEdit(page, 'Thursday')
    await to(dialog).fill('14:00')
    await dialog.getByRole('button', { name: 'Save' }).click()

    await expect(dialog.getByText(GENERIC)).toBeVisible()
    await expect(to(dialog)).toHaveValue('14:00')
  })
})

test.describe('Schedule settings: Delete the slot', () => {
  test('Delete removes the slot', async ({ page, request }) => {
    await openSettings(page, request, [
      ['thursday', '10:00', '13:00'],
      ['saturday', '10:00', '13:00'],
    ])

    const confirmation = await askToDelete(page, 'Thursday', DELETE_THURSDAY)
    await confirmation.getByRole('button', { name: 'Delete', exact: true }).click()

    await expect(confirmation).toBeHidden()
    await expect(line(page, 'Thursday')).toHaveCount(0)
    await expect(line(page, 'Saturday')).toHaveCount(1)
    await page.reload()
    await expect(line(page, 'Thursday')).toHaveCount(0)
  })

  for (const way of ['Cancel', 'Escape']) {
    test(`${way} keeps the slot`, async ({ page, request }) => {
      await openSettings(page, request, [['thursday', '10:00', '13:00']])

      const confirmation = await askToDelete(page, 'Thursday', DELETE_THURSDAY)
      if (way === 'Cancel') await confirmation.getByRole('button', { name: 'Cancel' }).click()
      else await page.keyboard.press('Escape')

      await expect(confirmation).toBeHidden()
      await page.reload()
      await expect(line(page, 'Thursday')).toHaveCount(1)
    })
  }

  test('when the server fails: the generic error in the confirmation', async ({ page, request }) => {
    await openSettings(page, request, [['thursday', '10:00', '13:00']])
    await page.route('**/delete', (route) => route.abort())

    const confirmation = await askToDelete(page, 'Thursday', DELETE_THURSDAY)
    await confirmation.getByRole('button', { name: 'Delete', exact: true }).click()

    await expect(confirmation.getByText(GENERIC)).toBeVisible()
    await expect(confirmation).toContainText(DELETE_THURSDAY)
  })
})
