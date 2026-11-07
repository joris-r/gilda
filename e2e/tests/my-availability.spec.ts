import { expect, test, type APIRequestContext, type Locator, type Page } from '@playwright/test'
import { PASSWORD, latestToken, uniqueEmail } from './helpers'

const GENERIC = 'Something went wrong. Try again.'

function uniqueSlug() {
  return `e2e-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

type Setup = { absences?: [string, string][]; note?: string }

/** Alice signs in on `page`, creates an association with `slots` and `setup`, and opens its My availability. */
async function openAvailability(
  page: Page,
  request: APIRequestContext,
  slots: [string, string, string][],
  setup: Setup = {},
) {
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
  for (const [first, last] of setup.absences ?? []) {
    const absence = await page.request.post(`/api/associations/${id}/absences`, { data: { first, last } })
    expect(absence.status()).toBe(201)
  }
  if (setup.note !== undefined) {
    const note = await page.request.put(`/api/associations/${id}/note`, { data: { text: setup.note } })
    expect(note.status()).toBe(200)
  }
  await page.goto(`/association/${slug}/availability`)
  await expect(page.locator('header').getByText('My availability')).toBeVisible()
  return slug
}

function selector(page: Page, text: string) {
  return page.locator('main').getByRole('listitem').filter({ hasText: text }).getByRole('combobox')
}

/** Waits for the preference saved on the only slot to be `value`, or none when `value` is null, as another page shows it. */
async function expectSaved(page: Page, slug: string, value: string | null) {
  const other = await page.context().newPage()
  await expect(async () => {
    await other.goto(`/association/${slug}/availability`)
    await expect(other.locator('main').getByRole('combobox')).toHaveValue(value ?? '', { timeout: 1000 })
  }).toPass()
  await other.close()
}

test.describe('My availability: My preferences', () => {
  test('each slot has a selector showing "—"', async ({ page, request }) => {
    await openAvailability(page, request, [
      ['thursday', '10:00', '13:00'],
      ['saturday', '10:00', '13:00'],
    ])

    await expect(selector(page, 'Thursday 10:00–13:00')).toHaveValue('')
    await expect(selector(page, 'Saturday 10:00–13:00')).toHaveValue('')
  })

  test('choosing a value saves it at once', async ({ page, request }) => {
    const slug = await openAvailability(page, request, [['thursday', '10:00', '13:00']])

    await selector(page, 'Thursday').selectOption({ label: 'Preferred' })

    await expectSaved(page, slug, 'preferred')
    await page.reload()
    await expect(selector(page, 'Thursday')).toHaveValue('preferred')
  })

  test('choosing another value replaces it', async ({ page, request }) => {
    const slug = await openAvailability(page, request, [['thursday', '10:00', '13:00']])
    await selector(page, 'Thursday').selectOption({ label: 'Preferred' })
    await expectSaved(page, slug, 'preferred')

    await selector(page, 'Thursday').selectOption({ label: 'Unavailable' })

    await expectSaved(page, slug, 'unavailable')
  })

  test('"—" deletes it', async ({ page, request }) => {
    const slug = await openAvailability(page, request, [['thursday', '10:00', '13:00']])
    await selector(page, 'Thursday').selectOption({ label: 'Possible' })
    await expectSaved(page, slug, 'possible')

    await selector(page, 'Thursday').selectOption({ label: '—' })

    await expectSaved(page, slug, null)
    await page.reload()
    await expect(selector(page, 'Thursday')).toHaveValue('')
  })

  test('each selector saves its own slot', async ({ page, request }) => {
    await openAvailability(page, request, [
      ['thursday', '10:00', '13:00'],
      ['saturday', '10:00', '13:00'],
    ])

    await selector(page, 'Saturday').selectOption({ label: 'Possible' })
    await selector(page, 'Thursday').selectOption({ label: 'Unavailable' })

    await expect(async () => {
      await page.reload()
      await expect(selector(page, 'Thursday')).toHaveValue('unavailable', { timeout: 1000 })
      await expect(selector(page, 'Saturday')).toHaveValue('possible', { timeout: 1000 })
    }).toPass()
  })

  test('when the server fails: the generic error', async ({ page, request }) => {
    await openAvailability(page, request, [['thursday', '10:00', '13:00']])
    await page.route('**/availability/preferences/**', (route) => route.fulfill({ status: 500, body: 'failure' }))

    await selector(page, 'Thursday').selectOption({ label: 'Preferred' })

    await expect(page.locator('main').getByText(GENERIC).filter({ visible: true })).toBeVisible()
  })
})

const NOV = ['2037-11-09', '2037-11-15'] as [string, string]
const NOV_SHOWN = 'Mon 9 Nov 2037 – Sun 15 Nov 2037'
const DEC = ['2037-12-21', '2038-01-03'] as [string, string]
const DEC_SHOWN = 'Mon 21 Dec 2037 – Sun 3 Jan 2038'
const DELETE_NOV = `Delete the absence of ${NOV_SHOWN}?`
const NOTE = 'Always group my registrations in pairs.'

function line(page: Page, text: string) {
  return page.locator('main').getByRole('listitem').filter({ hasText: text })
}

function from(dialog: Locator) {
  return dialog.getByLabel('From', { exact: true })
}

function to(dialog: Locator) {
  return dialog.getByLabel('To', { exact: true })
}

function noteText(dialog: Locator) {
  return dialog.getByLabel('Text', { exact: true })
}

/** What the Note for the managers section shows of `text`. */
function inNote(page: Page, text: string) {
  return page
    .locator('main section')
    .filter({ has: page.getByRole('heading', { name: 'Note for the managers', exact: true }) })
    .getByText(text, { exact: true })
    .filter({ visible: true })
}

async function openAddAbsence(page: Page) {
  await page.getByRole('button', { name: 'Add an absence' }).click()
  const dialog = page.getByRole('dialog', { name: 'Add an absence' })
  await expect(dialog).toBeVisible()
  return dialog
}

async function openEditAbsence(page: Page, text: string) {
  await line(page, text).getByRole('button', { name: 'Edit the absence' }).click()
  const dialog = page.getByRole('dialog', { name: 'Edit the absence' })
  await expect(dialog).toBeVisible()
  return dialog
}

async function askToDeleteAbsence(page: Page, text: string, question: string) {
  await line(page, text).getByRole('button', { name: 'Delete the absence' }).click()
  const confirmation = page.getByRole('dialog', { name: question, exact: true })
  await expect(confirmation).toBeVisible()
  return confirmation
}

async function openNote(page: Page) {
  await page.getByRole('button', { name: 'Edit the note' }).click()
  const dialog = page.getByRole('dialog', { name: 'Note for the managers' })
  await expect(dialog).toBeVisible()
  return dialog
}

test.describe('My availability: Add an absence', () => {
  test('opens the dialog "Add an absence", with From and To', async ({ page, request }) => {
    await openAvailability(page, request, [])

    const dialog = await openAddAbsence(page)

    await expect(from(dialog)).toBeVisible()
    await expect(to(dialog)).toBeVisible()
    await expect(dialog.getByRole('button', { name: 'Add absence' })).toBeVisible()
    await expect(dialog.getByRole('button', { name: 'Close' })).toBeVisible()
  })

  test('adding closes the dialog and shows the absence', async ({ page, request }) => {
    await openAvailability(page, request, [], { absences: [DEC] })

    const dialog = await openAddAbsence(page)
    await from(dialog).fill('2037-11-09')
    await to(dialog).fill('2037-11-15')
    await dialog.getByRole('button', { name: 'Add absence' }).click()

    await expect(dialog).toBeHidden()
    await expect(line(page, NOV_SHOWN)).toHaveCount(1)
    await expect(line(page, DEC_SHOWN)).toHaveCount(1)
    await page.reload()
    await expect(line(page, NOV_SHOWN)).toHaveCount(1)
  })

  for (const way of ['Cancel', 'the close button', 'Escape']) {
    test(`${way} closes it, changing nothing`, async ({ page, request }) => {
      await openAvailability(page, request, [])
      const dialog = await openAddAbsence(page)
      await from(dialog).fill('2037-11-09')
      await to(dialog).fill('2037-11-15')

      if (way === 'Cancel') await dialog.getByRole('button', { name: 'Cancel' }).click()
      else if (way === 'Escape') await page.keyboard.press('Escape')
      else await dialog.getByRole('button', { name: 'Close' }).click()

      await expect(dialog).toBeHidden()
      await page.reload()
      await expect(line(page, NOV_SHOWN)).toHaveCount(0)
    })
  }

  test('opened again after Cancel, its fields are empty', async ({ page, request }) => {
    await openAvailability(page, request, [])
    let dialog = await openAddAbsence(page)
    await from(dialog).fill('2037-11-09')
    await dialog.getByRole('button', { name: 'Cancel' }).click()

    dialog = await openAddAbsence(page)

    await expect(from(dialog)).toHaveValue('')
    await expect(to(dialog)).toHaveValue('')
  })

  test('opened again after adding, its fields are empty', async ({ page, request }) => {
    await openAvailability(page, request, [])
    let dialog = await openAddAbsence(page)
    await from(dialog).fill('2037-11-09')
    await to(dialog).fill('2037-11-15')
    await dialog.getByRole('button', { name: 'Add absence' }).click()
    await expect(dialog).toBeHidden()

    dialog = await openAddAbsence(page)

    await expect(from(dialog)).toHaveValue('')
    await expect(to(dialog)).toHaveValue('')
  })

  test('when the server fails: the generic error in the dialog, and what was typed stays', async ({
    page,
    request,
  }) => {
    await openAvailability(page, request, [])
    await page.route('**/availability/absences', (route) => route.fulfill({ status: 500, body: 'failure' }))

    const dialog = await openAddAbsence(page)
    await from(dialog).fill('2037-11-09')
    await to(dialog).fill('2037-11-15')
    await dialog.getByRole('button', { name: 'Add absence' }).click()

    await expect(dialog.getByText(GENERIC)).toBeVisible()
    await expect(from(dialog)).toHaveValue('2037-11-09')
    await expect(to(dialog)).toHaveValue('2037-11-15')
  })
})

test.describe('My availability: Edit the absence', () => {
  test('opens the dialog "Edit the absence", filled with the absence', async ({ page, request }) => {
    await openAvailability(page, request, [], { absences: [NOV, DEC] })

    const dialog = await openEditAbsence(page, DEC_SHOWN)

    await expect(from(dialog)).toHaveValue('2037-12-21')
    await expect(to(dialog)).toHaveValue('2038-01-03')
    await expect(dialog.getByRole('button', { name: 'Save' })).toBeVisible()
    await expect(dialog.getByRole('button', { name: 'Close' })).toBeVisible()
  })

  test('Save closes the dialog and shows the absence edited', async ({ page, request }) => {
    await openAvailability(page, request, [], { absences: [NOV] })

    const dialog = await openEditAbsence(page, NOV_SHOWN)
    await to(dialog).fill('2037-11-20')
    await dialog.getByRole('button', { name: 'Save' }).click()

    await expect(dialog).toBeHidden()
    await expect(line(page, 'Mon 9 Nov 2037 – Fri 20 Nov 2037')).toHaveCount(1)
    await expect(line(page, NOV_SHOWN)).toHaveCount(0)
    await page.reload()
    await expect(line(page, 'Mon 9 Nov 2037 – Fri 20 Nov 2037')).toHaveCount(1)
  })

  test('opened again after a Save, it is filled with the absence edited', async ({ page, request }) => {
    await openAvailability(page, request, [], { absences: [NOV] })
    let dialog = await openEditAbsence(page, NOV_SHOWN)
    await to(dialog).fill('2037-11-20')
    await dialog.getByRole('button', { name: 'Save' }).click()
    await expect(dialog).toBeHidden()

    dialog = await openEditAbsence(page, 'Fri 20 Nov 2037')

    await expect(to(dialog)).toHaveValue('2037-11-20')
  })

  test('Cancel closes it, changing nothing', async ({ page, request }) => {
    await openAvailability(page, request, [], { absences: [NOV] })

    const dialog = await openEditAbsence(page, NOV_SHOWN)
    await to(dialog).fill('2037-11-20')
    await dialog.getByRole('button', { name: 'Cancel' }).click()

    await expect(dialog).toBeHidden()
    await page.reload()
    await expect(line(page, NOV_SHOWN)).toHaveCount(1)
  })

  test('opened again after Cancel, it is filled with the absence', async ({ page, request }) => {
    await openAvailability(page, request, [], { absences: [NOV] })
    let dialog = await openEditAbsence(page, NOV_SHOWN)
    await to(dialog).fill('2037-11-20')
    await dialog.getByRole('button', { name: 'Cancel' }).click()

    dialog = await openEditAbsence(page, NOV_SHOWN)

    await expect(to(dialog)).toHaveValue('2037-11-15')
  })

  test('when the server fails: the generic error in the dialog', async ({ page, request }) => {
    await openAvailability(page, request, [], { absences: [NOV] })
    await page.route('**/edit', (route) => route.fulfill({ status: 500, body: 'failure' }))

    const dialog = await openEditAbsence(page, NOV_SHOWN)
    await to(dialog).fill('2037-11-20')
    await dialog.getByRole('button', { name: 'Save' }).click()

    await expect(dialog.getByText(GENERIC)).toBeVisible()
    await expect(to(dialog)).toHaveValue('2037-11-20')
  })
})

test.describe('My availability: Delete the absence', () => {
  test('Delete removes the absence', async ({ page, request }) => {
    await openAvailability(page, request, [], { absences: [NOV, DEC] })

    const confirmation = await askToDeleteAbsence(page, NOV_SHOWN, DELETE_NOV)
    await confirmation.getByRole('button', { name: 'Delete', exact: true }).click()

    await expect(confirmation).toBeHidden()
    await expect(line(page, NOV_SHOWN)).toHaveCount(0)
    await expect(line(page, DEC_SHOWN)).toHaveCount(1)
    await page.reload()
    await expect(line(page, NOV_SHOWN)).toHaveCount(0)
  })

  test('asks with the dates of the absence', async ({ page, request }) => {
    await openAvailability(page, request, [], { absences: [NOV, DEC] })

    await askToDeleteAbsence(page, DEC_SHOWN, `Delete the absence of ${DEC_SHOWN}?`)
  })

  for (const way of ['Cancel', 'Escape']) {
    test(`${way} keeps the absence`, async ({ page, request }) => {
      await openAvailability(page, request, [], { absences: [NOV] })

      const confirmation = await askToDeleteAbsence(page, NOV_SHOWN, DELETE_NOV)
      if (way === 'Cancel') await confirmation.getByRole('button', { name: 'Cancel' }).click()
      else await page.keyboard.press('Escape')

      await expect(confirmation).toBeHidden()
      await page.reload()
      await expect(line(page, NOV_SHOWN)).toHaveCount(1)
    })
  }

  test('when the server fails: the generic error in the confirmation', async ({ page, request }) => {
    await openAvailability(page, request, [], { absences: [NOV] })
    await page.route('**/delete', (route) => route.abort())

    const confirmation = await askToDeleteAbsence(page, NOV_SHOWN, DELETE_NOV)
    await confirmation.getByRole('button', { name: 'Delete', exact: true }).click()

    await expect(confirmation.getByText(GENERIC)).toBeVisible()
    await expect(confirmation).toContainText(DELETE_NOV)
  })
})

test.describe('My availability: Note for the managers', () => {
  test('the edit icon opens the dialog "Note for the managers", filled with the note', async ({
    page,
    request,
  }) => {
    await openAvailability(page, request, [], { note: NOTE })

    const dialog = await openNote(page)

    await expect(noteText(dialog)).toHaveValue(NOTE)
    await expect(dialog.getByRole('button', { name: 'Save' })).toBeVisible()
    await expect(dialog.getByRole('button', { name: 'Close' })).toBeVisible()
  })

  test('without a note, the dialog opens empty', async ({ page, request }) => {
    await openAvailability(page, request, [])

    const dialog = await openNote(page)

    await expect(noteText(dialog)).toHaveValue('')
  })

  test('Save closes the dialog and shows the note', async ({ page, request }) => {
    await openAvailability(page, request, [])

    const dialog = await openNote(page)
    await noteText(dialog).fill(NOTE)
    await dialog.getByRole('button', { name: 'Save' }).click()

    await expect(dialog).toBeHidden()
    await expect(inNote(page, NOTE)).toBeVisible()
    await page.reload()
    await expect(inNote(page, NOTE)).toBeVisible()
  })

  test('the Text takes several lines, kept once saved', async ({ page, request }) => {
    await openAvailability(page, request, [])
    let dialog = await openNote(page)
    await noteText(dialog).fill('Mornings only.')
    await noteText(dialog).press('Enter')
    await noteText(dialog).pressSequentially('Never on Sundays.')
    await dialog.getByRole('button', { name: 'Save' }).click()
    await expect(dialog).toBeHidden()

    await page.reload()
    dialog = await openNote(page)

    await expect(noteText(dialog)).toHaveValue('Mornings only.\nNever on Sundays.')
  })

  test('opened again after a Save, it is filled with the note saved', async ({ page, request }) => {
    await openAvailability(page, request, [], { note: NOTE })
    let dialog = await openNote(page)
    await noteText(dialog).fill('Mornings only.')
    await dialog.getByRole('button', { name: 'Save' }).click()
    await expect(dialog).toBeHidden()

    dialog = await openNote(page)

    await expect(noteText(dialog)).toHaveValue('Mornings only.')
  })

  test('saving an empty Text shows "None"', async ({ page, request }) => {
    await openAvailability(page, request, [], { note: NOTE })

    const dialog = await openNote(page)
    await noteText(dialog).fill('')
    await dialog.getByRole('button', { name: 'Save' }).click()

    await expect(dialog).toBeHidden()
    await expect(inNote(page, 'None')).toBeVisible()
    await expect(inNote(page, NOTE)).toHaveCount(0)
  })

  for (const way of ['Cancel', 'Escape']) {
    test(`${way} closes it, changing nothing`, async ({ page, request }) => {
      await openAvailability(page, request, [], { note: NOTE })
      const dialog = await openNote(page)
      await noteText(dialog).fill('Mornings only.')

      if (way === 'Cancel') await dialog.getByRole('button', { name: 'Cancel' }).click()
      else await page.keyboard.press('Escape')

      await expect(dialog).toBeHidden()
      await page.reload()
      await expect(inNote(page, NOTE)).toBeVisible()
    })
  }

  test('opened again after Cancel, it is filled with the note', async ({ page, request }) => {
    await openAvailability(page, request, [], { note: NOTE })
    let dialog = await openNote(page)
    await noteText(dialog).fill('Mornings only.')
    await dialog.getByRole('button', { name: 'Cancel' }).click()

    dialog = await openNote(page)

    await expect(noteText(dialog)).toHaveValue(NOTE)
  })

  test('when the server fails: the generic error in the dialog, and what was typed stays', async ({
    page,
    request,
  }) => {
    await openAvailability(page, request, [])
    await page.route('**/availability/note', (route) => route.fulfill({ status: 500, body: 'failure' }))

    const dialog = await openNote(page)
    await noteText(dialog).fill(NOTE)
    await dialog.getByRole('button', { name: 'Save' }).click()

    await expect(dialog.getByText(GENERIC)).toBeVisible()
    await expect(noteText(dialog)).toHaveValue(NOTE)
  })
})
