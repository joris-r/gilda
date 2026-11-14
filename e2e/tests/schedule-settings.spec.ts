import { expect, test, type APIRequestContext, type Locator, type Page } from '@playwright/test'
import { addClosure, addMember, addSlot as createSlot, createAssociation, setPeriod, signedIn } from './helpers'

const GENERIC = 'Something went wrong. Try again.'
const EXISTS = 'This slot already exists.'
const DELETE_THURSDAY = 'Delete the slot Thursday 10:00–13:00?'

type Setup = { closures?: [string, string, string?][]; period?: [string, string]; members?: string[] }

/** Alice signs in on `page`, creates an association with `slots` and `setup`, and opens its Schedule settings. */
async function openSettings(
  page: Page,
  request: APIRequestContext,
  slots: [string, string, string][] = [],
  setup: Setup = {},
) {
  await signedIn(page, request)
  const slug = await createAssociation(page.request)
  for (const [weekday, start, end] of slots) await createSlot(page.request, slug, weekday, start, end)
  for (const [first, last, label] of setup.closures ?? []) await addClosure(page.request, slug, first, last, label)
  if (setup.period) await setPeriod(page.request, slug, ...setup.period)
  for (const displayName of setup.members ?? []) await addMember(page.request, slug, displayName)
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
  // /planning/ui/schedule-settings/add-slot
  // /ui/forms/dialog
  test('opens the dialog "Add a slot", with Day, From and To', async ({ page, request }) => {
    await openSettings(page, request)

    const dialog = await openAdd(page)

    await expect(day(dialog)).toBeVisible()
    await expect(from(dialog)).toBeVisible()
    await expect(to(dialog)).toBeVisible()
    await expect(dialog.getByRole('button', { name: 'Add slot' })).toBeVisible()
    await expect(dialog.getByRole('button', { name: 'Close' })).toBeVisible()
  })

  // /planning/ui/schedule-settings/defaults
  test('opens with From and To at 09:00', async ({ page, request }) => {
    await openSettings(page, request)

    const dialog = await openAdd(page)

    await expect(from(dialog)).toHaveValue('09:00')
    await expect(to(dialog)).toHaveValue('09:00')
  })

  // /planning/ui/schedule-settings/defaults
  test('changing From sets To to the same time', async ({ page, request }) => {
    await openSettings(page, request)
    const dialog = await openAdd(page)

    await from(dialog).fill('14:00')

    await expect(to(dialog)).toHaveValue('14:00')
  })

  // /planning/ui/schedule-settings/defaults
  test('once To is changed, changing From leaves To as it is', async ({ page, request }) => {
    await openSettings(page, request)
    const dialog = await openAdd(page)

    await to(dialog).fill('12:00')
    await from(dialog).fill('10:00')

    await expect(from(dialog)).toHaveValue('10:00')
    await expect(to(dialog)).toHaveValue('12:00')
  })

  // /planning/ui/schedule-settings/add-slot
  // /planning/operations/add-slot/added
  // /planning/ui/schedule-settings/slots
  test('adding closes the dialog and shows the slot', async ({ page, request }) => {
    await openSettings(page, request, [['thursday', '10:00', '13:00']])

    await addSlot(page, 'Friday', '16:00', '19:00')

    await expect(line(page, 'Friday')).toContainText('16:00–19:00')
    await expect(line(page, 'Thursday')).toContainText('10:00–13:00')
    await page.reload()
    await expect(line(page, 'Friday')).toContainText('16:00–19:00')
  })

  // /planning/ui/schedule-settings/next-slot
  test('after a slot is added, the next dialog opens with its Day, and From and To at its end', async ({
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

  // /planning/ui/schedule-settings/next-slot
  test('in the next dialog, To follows From again', async ({ page, request }) => {
    await openSettings(page, request)
    await addSlot(page, 'Friday', '09:00', '13:00')

    const dialog = await openAdd(page)
    await from(dialog).fill('15:00')

    await expect(to(dialog)).toHaveValue('15:00')
  })

  // /planning/ui/schedule-settings/next-slot
  test('the slot added last sets the next dialog', async ({ page, request }) => {
    await openSettings(page, request)
    await addSlot(page, 'Friday', '09:00', '13:00')
    await addSlot(page, 'Saturday', '14:00', '17:30')

    const dialog = await openAdd(page)

    await expect(day(dialog)).toHaveValue('saturday')
    await expect(from(dialog)).toHaveValue('17:30')
    await expect(to(dialog)).toHaveValue('17:30')
  })

  // /planning/ui/schedule-settings/next-slot
  // /planning/ui/schedule-settings/defaults
  test('after a slot is edited, Add a slot still opens with From and To at 09:00', async ({ page, request }) => {
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
    // /ui/forms/close
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

  // /planning/ui/schedule-settings/defaults
  // /ui/forms/close
  test('opened again after Cancel, it opens with From and To at 09:00', async ({ page, request }) => {
    await openSettings(page, request)
    let dialog = await openAdd(page)
    await from(dialog).fill('16:00')
    await to(dialog).fill('19:00')
    await dialog.getByRole('button', { name: 'Cancel' }).click()

    dialog = await openAdd(page)

    await expect(from(dialog)).toHaveValue('09:00')
    await expect(to(dialog)).toHaveValue('09:00')
  })

  // /planning/ui/schedule-settings/exists
  // /ui/forms/failure
  // /planning/operations/add-slot/exists
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

  // /ui/forms/failure
  // /ui/errors/generic
  // /ui/errors/kept
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
  // /planning/ui/schedule-settings/edit-slot
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

  // /planning/ui/schedule-settings/edit-slot
  test('changing From leaves To as it is', async ({ page, request }) => {
    await openSettings(page, request, [['thursday', '10:00', '13:00']])
    const dialog = await openEdit(page, 'Thursday')

    await from(dialog).fill('09:00')

    await expect(to(dialog)).toHaveValue('13:00')
  })

  // /planning/ui/schedule-settings/edit-slot
  // /planning/operations/edit-slot/edited
  // /ui/forms/success
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

  // /planning/ui/schedule-settings/edit-slot
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

  // /planning/ui/schedule-settings/edit-exists
  // /ui/forms/failure
  // /planning/operations/edit-slot/exists
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

  // /ui/forms/close
  test('Cancel closes it, changing nothing', async ({ page, request }) => {
    await openSettings(page, request, [['thursday', '10:00', '13:00']])

    const dialog = await openEdit(page, 'Thursday')
    await to(dialog).fill('14:00')
    await dialog.getByRole('button', { name: 'Cancel' }).click()

    await expect(dialog).toBeHidden()
    await page.reload()
    await expect(line(page, 'Thursday')).toContainText('10:00–13:00')
  })

  // /ui/forms/close
  test('opened again after Cancel, it is filled with the slot', async ({ page, request }) => {
    await openSettings(page, request, [['thursday', '10:00', '13:00']])
    let dialog = await openEdit(page, 'Thursday')
    await to(dialog).fill('14:00')
    await dialog.getByRole('button', { name: 'Cancel' }).click()

    dialog = await openEdit(page, 'Thursday')

    await expect(to(dialog)).toHaveValue('13:00')
  })

  // /ui/forms/failure
  // /ui/errors/generic
  // /ui/errors/kept
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
  // /planning/ui/schedule-settings/delete-slot
  // /planning/operations/delete-slot/deleted
  // /ui/forms/delete
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
    // /ui/forms/cancel
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

  // /ui/forms/failure
  // /ui/errors/generic
  test('when the server fails: the generic error in the confirmation', async ({ page, request }) => {
    await openSettings(page, request, [['thursday', '10:00', '13:00']])
    await page.route('**/delete', (route) => route.abort())

    const confirmation = await askToDelete(page, 'Thursday', DELETE_THURSDAY)
    await confirmation.getByRole('button', { name: 'Delete', exact: true }).click()

    await expect(confirmation.getByText(GENERIC)).toBeVisible()
    await expect(confirmation).toContainText(DELETE_THURSDAY)
  })
})

const PERIOD_SHOWN = 'Mon 2 Nov 2026 – Wed 25 Nov 2026'
const CLEAR = 'Clear the planning period?'
const FETE = ['2026-11-14', '2026-11-14', 'Fête du quartier'] as [string, string, string]
const DELETE_FETE = 'Delete the closure "Fête du quartier"?'

function label(dialog: Locator) {
  return dialog.getByLabel('Label', { exact: true })
}

function period(page: Page) {
  return page.locator('main').getByText(PERIOD_SHOWN)
}

async function openPeriod(page: Page) {
  await page.getByRole('button', { name: 'Edit the period' }).click()
  const dialog = page.getByRole('dialog', { name: 'Planning period' })
  await expect(dialog).toBeVisible()
  return dialog
}

async function askToClear(page: Page) {
  await page.getByRole('button', { name: 'Clear the period' }).click()
  const confirmation = page.getByRole('dialog', { name: CLEAR, exact: true })
  await expect(confirmation).toBeVisible()
  return confirmation
}

async function openAddClosure(page: Page) {
  await page.getByRole('button', { name: 'Add a closure' }).click()
  const dialog = page.getByRole('dialog', { name: 'Add a closure' })
  await expect(dialog).toBeVisible()
  return dialog
}

async function openEditClosure(page: Page, text: string) {
  await line(page, text).getByRole('button', { name: 'Edit the closure' }).click()
  const dialog = page.getByRole('dialog', { name: 'Edit the closure' })
  await expect(dialog).toBeVisible()
  return dialog
}

async function askToDeleteClosure(page: Page, text: string, question: string) {
  await line(page, text).getByRole('button', { name: 'Delete the closure' }).click()
  const confirmation = page.getByRole('dialog', { name: question, exact: true })
  await expect(confirmation).toBeVisible()
  return confirmation
}

test.describe('Schedule settings: Planning period', () => {
  // /planning/ui/schedule-settings/edit-period
  test('the edit icon opens the dialog "Planning period", with From and To', async ({ page, request }) => {
    await openSettings(page, request)

    const dialog = await openPeriod(page)

    await expect(from(dialog)).toBeVisible()
    await expect(to(dialog)).toBeVisible()
    await expect(dialog.getByRole('button', { name: 'Save' })).toBeVisible()
    await expect(dialog.getByRole('button', { name: 'Close' })).toBeVisible()
  })

  // /planning/ui/schedule-settings/edit-period
  // /ui/forms/edit
  test('the dialog opens filled with the period', async ({ page, request }) => {
    await openSettings(page, request, [], { period: ['2026-11-02', '2026-11-25'] })

    const dialog = await openPeriod(page)

    await expect(from(dialog)).toHaveValue('2026-11-02')
    await expect(to(dialog)).toHaveValue('2026-11-25')
  })

  // /planning/ui/schedule-settings/edit-period
  // /planning/operations/set-planning-period/set
  // /planning/ui/schedule-settings/period
  // /planning/ui/schedule-settings/clear-period
  test('Save closes the dialog and shows the period, with its delete icon', async ({ page, request }) => {
    await openSettings(page, request)
    await expect(page.getByRole('button', { name: 'Clear the period' })).toHaveCount(0)

    const dialog = await openPeriod(page)
    await from(dialog).fill('2026-11-02')
    await to(dialog).fill('2026-11-25')
    await dialog.getByRole('button', { name: 'Save' }).click()

    await expect(dialog).toBeHidden()
    await expect(period(page)).toBeVisible()
    await expect(page.getByRole('button', { name: 'Clear the period' })).toBeVisible()
    await page.reload()
    await expect(period(page)).toBeVisible()
  })

  // /planning/ui/schedule-settings/edit-period
  // /planning/operations/set-planning-period/set
  test('opened again after a Save, it is filled with the period saved', async ({ page, request }) => {
    await openSettings(page, request, [], { period: ['2026-11-02', '2026-11-25'] })
    let dialog = await openPeriod(page)
    await to(dialog).fill('2026-11-30')
    await dialog.getByRole('button', { name: 'Save' }).click()
    await expect(dialog).toBeHidden()

    dialog = await openPeriod(page)

    await expect(from(dialog)).toHaveValue('2026-11-02')
    await expect(to(dialog)).toHaveValue('2026-11-30')
  })

  for (const way of ['Cancel', 'the close button', 'Escape']) {
    // /ui/forms/close
    test(`${way} closes it, changing nothing`, async ({ page, request }) => {
      await openSettings(page, request, [], { period: ['2026-11-02', '2026-11-25'] })
      const dialog = await openPeriod(page)
      await to(dialog).fill('2026-11-30')

      if (way === 'Cancel') await dialog.getByRole('button', { name: 'Cancel' }).click()
      else if (way === 'Escape') await page.keyboard.press('Escape')
      else await dialog.getByRole('button', { name: 'Close' }).click()

      await expect(dialog).toBeHidden()
      await page.reload()
      await expect(period(page)).toBeVisible()
    })
  }

  // /ui/forms/close
  test('opened again after Cancel, it is filled with the period', async ({ page, request }) => {
    await openSettings(page, request, [], { period: ['2026-11-02', '2026-11-25'] })
    let dialog = await openPeriod(page)
    await to(dialog).fill('2026-11-30')
    await dialog.getByRole('button', { name: 'Cancel' }).click()

    dialog = await openPeriod(page)

    await expect(to(dialog)).toHaveValue('2026-11-25')
  })

  // /ui/forms/failure
  // /ui/errors/generic
  // /ui/errors/kept
  test('when the server fails: the generic error in the dialog, and what was typed stays', async ({
    page,
    request,
  }) => {
    await openSettings(page, request)
    await page.route('**/settings/period', (route) => route.fulfill({ status: 500, body: 'failure' }))

    const dialog = await openPeriod(page)
    await from(dialog).fill('2026-11-02')
    await to(dialog).fill('2026-11-25')
    await dialog.getByRole('button', { name: 'Save' }).click()

    await expect(dialog.getByText(GENERIC)).toBeVisible()
    await expect(from(dialog)).toHaveValue('2026-11-02')
    await expect(to(dialog)).toHaveValue('2026-11-25')
  })

  // /planning/ui/schedule-settings/clear-period
  // /planning/operations/clear-planning-period/cleared
  test('Clear removes the period and its delete icon', async ({ page, request }) => {
    await openSettings(page, request, [], { period: ['2026-11-02', '2026-11-25'] })

    const confirmation = await askToClear(page)
    await confirmation.getByRole('button', { name: 'Clear', exact: true }).click()

    await expect(confirmation).toBeHidden()
    await expect(period(page)).toHaveCount(0)
    await expect(page.getByRole('button', { name: 'Clear the period' })).toHaveCount(0)
    await page.reload()
    await expect(period(page)).toHaveCount(0)
  })

  for (const way of ['Cancel', 'Escape']) {
    // /ui/forms/cancel
    test(`${way} keeps the period`, async ({ page, request }) => {
      await openSettings(page, request, [], { period: ['2026-11-02', '2026-11-25'] })

      const confirmation = await askToClear(page)
      if (way === 'Cancel') await confirmation.getByRole('button', { name: 'Cancel' }).click()
      else await page.keyboard.press('Escape')

      await expect(confirmation).toBeHidden()
      await page.reload()
      await expect(period(page)).toBeVisible()
    })
  }

  // /ui/forms/failure
  // /ui/errors/generic
  test('when Clear fails: the generic error in the confirmation', async ({ page, request }) => {
    await openSettings(page, request, [], { period: ['2026-11-02', '2026-11-25'] })
    await page.route('**/period/clear', (route) => route.abort())

    const confirmation = await askToClear(page)
    await confirmation.getByRole('button', { name: 'Clear', exact: true }).click()

    await expect(confirmation.getByText(GENERIC)).toBeVisible()
  })
})

test.describe('Schedule settings: Add a closure', () => {
  // /planning/ui/schedule-settings/add-closure
  test('opens the dialog "Add a closure", with From, To and Label', async ({ page, request }) => {
    await openSettings(page, request)

    const dialog = await openAddClosure(page)

    await expect(from(dialog)).toBeVisible()
    await expect(to(dialog)).toBeVisible()
    await expect(label(dialog)).toBeVisible()
    await expect(dialog.getByRole('button', { name: 'Add closure' })).toBeVisible()
    await expect(dialog.getByRole('button', { name: 'Close' })).toBeVisible()
  })

  // /planning/ui/schedule-settings/add-closure
  // /planning/operations/add-closure/added
  // /planning/ui/schedule-settings/closures
  test('adding closes the dialog and shows the closure', async ({ page, request }) => {
    await openSettings(page, request, [], { closures: [['2026-12-24', '2027-01-01', "Fêtes de fin d'année"]] })

    const dialog = await openAddClosure(page)
    await from(dialog).fill('2026-11-14')
    await to(dialog).fill('2026-11-14')
    await label(dialog).fill('Fête du quartier')
    await dialog.getByRole('button', { name: 'Add closure' }).click()

    await expect(dialog).toBeHidden()
    await expect(line(page, 'Fête du quartier')).toContainText('Sat 14 Nov 2026')
    await expect(line(page, "Fêtes de fin d'année")).toBeVisible()
    await page.reload()
    await expect(line(page, 'Fête du quartier')).toContainText('Sat 14 Nov 2026')
  })

  // /planning/operations/add-closure/added
  // /planning/ui/schedule-settings/closures
  test('without a label, the closure shows its dates', async ({ page, request }) => {
    await openSettings(page, request)

    const dialog = await openAddClosure(page)
    await from(dialog).fill('2026-12-24')
    await to(dialog).fill('2027-01-01')
    await dialog.getByRole('button', { name: 'Add closure' }).click()

    await expect(dialog).toBeHidden()
    await expect(line(page, 'Thu 24 Dec 2026 – Fri 1 Jan 2027')).toBeVisible()
  })

  for (const way of ['Cancel', 'the close button', 'Escape']) {
    // /ui/forms/close
    test(`${way} closes it, changing nothing`, async ({ page, request }) => {
      await openSettings(page, request)
      const dialog = await openAddClosure(page)
      await from(dialog).fill('2026-11-14')
      await to(dialog).fill('2026-11-14')
      await label(dialog).fill('Fête du quartier')

      if (way === 'Cancel') await dialog.getByRole('button', { name: 'Cancel' }).click()
      else if (way === 'Escape') await page.keyboard.press('Escape')
      else await dialog.getByRole('button', { name: 'Close' }).click()

      await expect(dialog).toBeHidden()
      await page.reload()
      await expect(line(page, 'Fête du quartier')).toHaveCount(0)
    })
  }

  // /ui/forms/close
  test('opened again after Cancel, its fields are empty', async ({ page, request }) => {
    await openSettings(page, request)
    let dialog = await openAddClosure(page)
    await from(dialog).fill('2026-11-14')
    await label(dialog).fill('Fête du quartier')
    await dialog.getByRole('button', { name: 'Cancel' }).click()

    dialog = await openAddClosure(page)

    await expect(from(dialog)).toHaveValue('')
    await expect(to(dialog)).toHaveValue('')
    await expect(label(dialog)).toHaveValue('')
  })

  // /planning/ui/schedule-settings/add-closure
  test('opened again after adding, its fields are empty', async ({ page, request }) => {
    await openSettings(page, request)
    let dialog = await openAddClosure(page)
    await from(dialog).fill('2026-11-14')
    await to(dialog).fill('2026-11-14')
    await label(dialog).fill('Fête du quartier')
    await dialog.getByRole('button', { name: 'Add closure' }).click()
    await expect(dialog).toBeHidden()

    dialog = await openAddClosure(page)

    await expect(from(dialog)).toHaveValue('')
    await expect(label(dialog)).toHaveValue('')
  })

  // /ui/forms/failure
  // /ui/errors/generic
  // /ui/errors/kept
  test('when the server fails: the generic error in the dialog, and what was typed stays', async ({
    page,
    request,
  }) => {
    await openSettings(page, request)
    await page.route('**/settings/closures', (route) => route.fulfill({ status: 500, body: 'failure' }))

    const dialog = await openAddClosure(page)
    await from(dialog).fill('2026-11-14')
    await to(dialog).fill('2026-11-14')
    await label(dialog).fill('Fête du quartier')
    await dialog.getByRole('button', { name: 'Add closure' }).click()

    await expect(dialog.getByText(GENERIC)).toBeVisible()
    await expect(from(dialog)).toHaveValue('2026-11-14')
    await expect(label(dialog)).toHaveValue('Fête du quartier')
  })
})

test.describe('Schedule settings: Edit the closure', () => {
  // /planning/ui/schedule-settings/edit-closure
  test('opens the dialog "Edit the closure", filled with the closure', async ({ page, request }) => {
    await openSettings(page, request, [], {
      closures: [FETE, ['2026-12-24', '2027-01-01', "Fêtes de fin d'année"]],
    })

    const dialog = await openEditClosure(page, "Fêtes de fin d'année")

    await expect(from(dialog)).toHaveValue('2026-12-24')
    await expect(to(dialog)).toHaveValue('2027-01-01')
    await expect(label(dialog)).toHaveValue("Fêtes de fin d'année")
    await expect(dialog.getByRole('button', { name: 'Save' })).toBeVisible()
    await expect(dialog.getByRole('button', { name: 'Close' })).toBeVisible()
  })

  // /planning/ui/schedule-settings/edit-closure
  test('a closure without a label opens with an empty Label', async ({ page, request }) => {
    await openSettings(page, request, [], { closures: [['2026-11-14', '2026-11-14']] })

    const dialog = await openEditClosure(page, 'Sat 14 Nov 2026')

    await expect(label(dialog)).toHaveValue('')
  })

  // /planning/ui/schedule-settings/edit-closure
  // /planning/operations/edit-closure/edited
  test('Save closes the dialog and shows the closure edited', async ({ page, request }) => {
    await openSettings(page, request, [], { closures: [FETE] })

    const dialog = await openEditClosure(page, 'Fête du quartier')
    await to(dialog).fill('2026-11-15')
    await label(dialog).fill('Fête élargie')
    await dialog.getByRole('button', { name: 'Save' }).click()

    await expect(dialog).toBeHidden()
    await expect(line(page, 'Fête élargie')).toContainText('Sat 14 Nov 2026 – Sun 15 Nov 2026')
    await expect(line(page, 'Fête du quartier')).toHaveCount(0)
    await page.reload()
    await expect(line(page, 'Fête élargie')).toContainText('Sat 14 Nov 2026 – Sun 15 Nov 2026')
  })

  // /planning/ui/schedule-settings/edit-closure
  test('opened again after a Save, it is filled with the closure edited', async ({ page, request }) => {
    await openSettings(page, request, [], { closures: [FETE] })
    let dialog = await openEditClosure(page, 'Fête du quartier')
    await label(dialog).fill('Fête élargie')
    await dialog.getByRole('button', { name: 'Save' }).click()
    await expect(dialog).toBeHidden()

    dialog = await openEditClosure(page, 'Fête élargie')

    await expect(label(dialog)).toHaveValue('Fête élargie')
  })

  // /ui/forms/close
  test('Cancel closes it, changing nothing', async ({ page, request }) => {
    await openSettings(page, request, [], { closures: [FETE] })

    const dialog = await openEditClosure(page, 'Fête du quartier')
    await label(dialog).fill('Fête élargie')
    await dialog.getByRole('button', { name: 'Cancel' }).click()

    await expect(dialog).toBeHidden()
    await page.reload()
    await expect(line(page, 'Fête du quartier')).toHaveCount(1)
  })

  // /ui/forms/close
  test('opened again after Cancel, it is filled with the closure', async ({ page, request }) => {
    await openSettings(page, request, [], { closures: [FETE] })
    let dialog = await openEditClosure(page, 'Fête du quartier')
    await label(dialog).fill('Fête élargie')
    await dialog.getByRole('button', { name: 'Cancel' }).click()

    dialog = await openEditClosure(page, 'Fête du quartier')

    await expect(label(dialog)).toHaveValue('Fête du quartier')
  })

  // /ui/forms/failure
  // /ui/errors/generic
  // /ui/errors/kept
  test('when the server fails: the generic error in the dialog', async ({ page, request }) => {
    await openSettings(page, request, [], { closures: [FETE] })
    await page.route('**/edit', (route) => route.fulfill({ status: 500, body: 'failure' }))

    const dialog = await openEditClosure(page, 'Fête du quartier')
    await label(dialog).fill('Fête élargie')
    await dialog.getByRole('button', { name: 'Save' }).click()

    await expect(dialog.getByText(GENERIC)).toBeVisible()
    await expect(label(dialog)).toHaveValue('Fête élargie')
  })
})

test.describe('Schedule settings: Delete the closure', () => {
  // /planning/ui/schedule-settings/delete-closure
  // /planning/operations/delete-closure/deleted
  test('Delete removes the closure', async ({ page, request }) => {
    await openSettings(page, request, [], {
      closures: [FETE, ['2026-12-24', '2027-01-01', "Fêtes de fin d'année"]],
    })

    const confirmation = await askToDeleteClosure(page, 'Fête du quartier', DELETE_FETE)
    await confirmation.getByRole('button', { name: 'Delete', exact: true }).click()

    await expect(confirmation).toBeHidden()
    await expect(line(page, 'Fête du quartier')).toHaveCount(0)
    await expect(line(page, "Fêtes de fin d'année")).toHaveCount(1)
    await page.reload()
    await expect(line(page, 'Fête du quartier')).toHaveCount(0)
  })

  // /planning/ui/schedule-settings/delete-closure
  test('asks with the label, quotes included', async ({ page, request }) => {
    await openSettings(page, request, [], { closures: [['2026-12-24', '2027-01-01', "Fêtes de fin d'année"]] })

    await askToDeleteClosure(page, "Fêtes de fin d'année", 'Delete the closure "Fêtes de fin d\'année"?')
  })

  // /planning/ui/schedule-settings/delete-closure
  test('without a label, asks with the dates', async ({ page, request }) => {
    await openSettings(page, request, [], { closures: [['2026-11-14', '2026-11-14']] })

    await askToDeleteClosure(page, 'Sat 14 Nov 2026', 'Delete the closure of Sat 14 Nov 2026?')
  })

  for (const way of ['Cancel', 'Escape']) {
    // /ui/forms/cancel
    test(`${way} keeps the closure`, async ({ page, request }) => {
      await openSettings(page, request, [], { closures: [FETE] })

      const confirmation = await askToDeleteClosure(page, 'Fête du quartier', DELETE_FETE)
      if (way === 'Cancel') await confirmation.getByRole('button', { name: 'Cancel' }).click()
      else await page.keyboard.press('Escape')

      await expect(confirmation).toBeHidden()
      await page.reload()
      await expect(line(page, 'Fête du quartier')).toHaveCount(1)
    })
  }

  // /ui/forms/failure
  // /ui/errors/generic
  test('when the server fails: the generic error in the confirmation', async ({ page, request }) => {
    await openSettings(page, request, [], { closures: [FETE] })
    await page.route('**/delete', (route) => route.abort())

    const confirmation = await askToDeleteClosure(page, 'Fête du quartier', DELETE_FETE)
    await confirmation.getByRole('button', { name: 'Delete', exact: true }).click()

    await expect(confirmation.getByText(GENERIC)).toBeVisible()
    await expect(confirmation).toContainText(DELETE_FETE)
  })
})

function preferences(page: Page) {
  return page.locator('main section').filter({ has: page.getByRole('heading', { name: "Members' preferences" }) })
}

/** The selector of `member` in the column `column` (0 for the first slot) of Members' preferences. */
function cell(page: Page, member: string, column: number) {
  return preferences(page).getByRole('row').filter({ hasText: member }).getByRole('combobox').nth(column)
}

test.describe("Schedule settings: Members' preferences", () => {
  // /planning/ui/schedule-settings/preferences
  test('a selector per member and slot, showing "—"', async ({ page, request }) => {
    await openSettings(
      page,
      request,
      [
        ['thursday', '10:00', '13:00'],
        ['saturday', '10:00', '13:00'],
      ],
      { members: ['Bruno'] },
    )

    await expect(preferences(page).getByRole('combobox')).toHaveCount(4)
    await expect(cell(page, 'Alice', 0)).toHaveValue('')
    await expect(cell(page, 'Bruno', 1)).toHaveValue('')
  })

  // /planning/ui/schedule-settings/set-preference
  // /planning/operations/set-preference/set
  test('choosing a value saves it at once', async ({ page, request }) => {
    await openSettings(
      page,
      request,
      [
        ['thursday', '10:00', '13:00'],
        ['saturday', '10:00', '13:00'],
      ],
      { members: ['Bruno'] },
    )

    await cell(page, 'Bruno', 1).selectOption({ label: 'Unavailable' })

    await expect(async () => {
      await page.reload()
      await expect(cell(page, 'Bruno', 1)).toHaveValue('unavailable', { timeout: 1000 })
    }).toPass()
    await expect(cell(page, 'Bruno', 0)).toHaveValue('')
    await expect(cell(page, 'Alice', 1)).toHaveValue('')
  })

  // /planning/ui/schedule-settings/set-preference
  // /planning/operations/delete-preference/deleted
  test('"—" deletes it', async ({ page, request }) => {
    await openSettings(page, request, [['thursday', '10:00', '13:00']], { members: ['Bruno'] })
    await cell(page, 'Bruno', 0).selectOption({ label: 'Possible' })
    await expect(async () => {
      await page.reload()
      await expect(cell(page, 'Bruno', 0)).toHaveValue('possible', { timeout: 1000 })
    }).toPass()

    await cell(page, 'Bruno', 0).selectOption({ label: '—' })

    await expect(async () => {
      await page.reload()
      await expect(cell(page, 'Bruno', 0)).toHaveValue('', { timeout: 1000 })
    }).toPass()
  })

  // /planning/ui/schedule-settings/preferences
  test('a slot added shows its column at once', async ({ page, request }) => {
    await openSettings(page, request, [['thursday', '10:00', '13:00']], { members: ['Bruno'] })

    await addSlot(page, 'Saturday', '10:00', '13:00')

    await expect(preferences(page).getByText('Sat 10:00–13:00')).toBeVisible()
    await expect(preferences(page).getByRole('row').filter({ hasText: 'Bruno' }).getByRole('combobox')).toHaveCount(2)
  })

  // /planning/ui/schedule-settings/preferences
  // /planning/operations/delete-slot/deleted
  test('a slot deleted leaves its column at once', async ({ page, request }) => {
    await openSettings(
      page,
      request,
      [
        ['thursday', '10:00', '13:00'],
        ['saturday', '10:00', '13:00'],
      ],
      { members: ['Bruno'] },
    )

    const confirmation = await askToDelete(page, 'Thursday', DELETE_THURSDAY)
    await confirmation.getByRole('button', { name: 'Delete', exact: true }).click()

    await expect(confirmation).toBeHidden()
    await expect(preferences(page).getByText('Thu 10:00–13:00')).toHaveCount(0)
    await expect(preferences(page).getByRole('row').filter({ hasText: 'Bruno' }).getByRole('combobox')).toHaveCount(1)
  })

  // /ui/errors/generic
  test('when the server fails: the generic error', async ({ page, request }) => {
    await openSettings(page, request, [['thursday', '10:00', '13:00']], { members: ['Bruno'] })
    await page.route('**/settings/preferences/**', (route) => route.fulfill({ status: 500, body: 'failure' }))

    await cell(page, 'Bruno', 0).selectOption({ label: 'Preferred' })

    await expect(page.locator('main').getByText(GENERIC).filter({ visible: true })).toBeVisible()
  })
})

const REPLACE = 'Replace the share link? The current link no longer shows the Schedule.'
const REVOKE = 'Revoke the share link? It no longer shows the Schedule.'

function shareLink(page: Page) {
  return page.locator('main').getByText(/\/shared\/[\w-]+/)
}

/** The share link that Schedule settings shows. */
async function shownLink(page: Page) {
  const text = (await shareLink(page).textContent()) ?? ''
  const match = /https?:\/\/\S+\/shared\/[\w-]+/.exec(text)
  expect(match).not.toBeNull()
  return match![0]
}

/** Creates the share link when there is none, and returns it. */
async function createLink(page: Page) {
  await page.getByRole('button', { name: 'Create a share link' }).click()
  await expect(shareLink(page)).toBeVisible()
  return shownLink(page)
}

async function askToReplace(page: Page) {
  await page.getByRole('button', { name: 'Create a share link' }).click()
  const confirmation = page.getByRole('dialog', { name: REPLACE, exact: true })
  await expect(confirmation).toBeVisible()
  return confirmation
}

async function askToRevoke(page: Page) {
  await page.getByRole('button', { name: 'Revoke the share link' }).click()
  const confirmation = page.getByRole('dialog', { name: REVOKE, exact: true })
  await expect(confirmation).toBeVisible()
  return confirmation
}

test.describe('Schedule settings: Share link', () => {
  // /planning/ui/schedule-settings/create-link
  // /planning/operations/create-share-link/created
  // /planning/ui/schedule-settings/share-link
  test('without a link, "Create a share link" creates it at once and shows it', async ({ page, request }) => {
    await openSettings(page, request)
    await expect(shareLink(page)).toHaveCount(0)

    await page.getByRole('button', { name: 'Create a share link' }).click()

    await expect(page.getByRole('dialog', { name: REPLACE, exact: true })).toBeHidden()
    await expect(shareLink(page)).toBeVisible()
    await expect(page.getByRole('button', { name: 'Copy', exact: true })).toBeVisible()
    const link = await shownLink(page)
    await page.reload()
    expect(await shownLink(page)).toBe(link)
  })

  // /planning/ui/schedule-settings/copy
  test('"Copy" copies the link and shows "Link copied."', async ({ page, request, context }) => {
    await context.grantPermissions(['clipboard-read', 'clipboard-write'])
    await openSettings(page, request)
    const link = await createLink(page)

    await page.getByRole('button', { name: 'Copy', exact: true }).click()

    await expect(page.getByText('Link copied.')).toBeVisible()
    expect(await page.evaluate(() => navigator.clipboard.readText())).toBe(link)
  })

  // /planning/ui/shared-schedule/shown
  test('the link opens the Shared schedule', async ({ page, request, browser }) => {
    await openSettings(page, request)
    const link = await createLink(page)

    const visitor = await browser.newPage()
    await visitor.goto(link)

    await expect(visitor.locator('header')).toContainText('Jardin partagé')
    await expect(visitor.locator('main').getByRole('heading', { name: /^Week \d+$/ }).first()).toBeVisible()
    await visitor.close()
  })

  // /planning/ui/schedule-settings/create-link
  // /planning/operations/create-share-link/created
  // /planning/ui/shared-schedule/invalid
  test('with a link, "Create a share link" asks first; "Replace" shows a new link', async ({ page, request, browser }) => {
    await openSettings(page, request)
    const previous = await createLink(page)

    const confirmation = await askToReplace(page)
    await confirmation.getByRole('button', { name: 'Replace', exact: true }).click()

    await expect(confirmation).toBeHidden()
    await expect(async () => expect(await shownLink(page)).not.toBe(previous)).toPass()
    const visitor = await browser.newPage()
    await visitor.goto(previous)
    await expect(visitor.getByText('This link is no longer valid.')).toBeVisible()
    await visitor.close()
  })

  for (const way of ['Cancel', 'Escape']) {
    // /ui/forms/cancel
    test(`${way} keeps the link instead of replacing it`, async ({ page, request }) => {
      await openSettings(page, request)
      const link = await createLink(page)

      const confirmation = await askToReplace(page)
      if (way === 'Cancel') await confirmation.getByRole('button', { name: 'Cancel' }).click()
      else await page.keyboard.press('Escape')

      await expect(confirmation).toBeHidden()
      await page.reload()
      expect(await shownLink(page)).toBe(link)
    })
  }

  // /planning/ui/schedule-settings/revoke-link
  // /planning/operations/revoke-share-link/revoked
  // /planning/ui/schedule-settings/share-link
  // /planning/ui/shared-schedule/invalid
  test('the delete icon asks first; "Revoke" shows None', async ({ page, request, browser }) => {
    await openSettings(page, request)
    const link = await createLink(page)

    const confirmation = await askToRevoke(page)
    await confirmation.getByRole('button', { name: 'Revoke', exact: true }).click()

    await expect(confirmation).toBeHidden()
    await expect(shareLink(page)).toHaveCount(0)
    await expect(page.getByRole('button', { name: 'Copy', exact: true })).toBeHidden()
    await expect(page.getByRole('button', { name: 'Revoke the share link' })).toBeHidden()
    const visitor = await browser.newPage()
    await visitor.goto(link)
    await expect(visitor.getByText('This link is no longer valid.')).toBeVisible()
    await visitor.close()
  })

  // /planning/ui/schedule-settings/create-link
  test('after Revoke, "Create a share link" creates a new one at once', async ({ page, request }) => {
    await openSettings(page, request)
    await createLink(page)
    const confirmation = await askToRevoke(page)
    await confirmation.getByRole('button', { name: 'Revoke', exact: true }).click()
    await expect(shareLink(page)).toHaveCount(0)

    await page.getByRole('button', { name: 'Create a share link' }).click()

    await expect(page.getByRole('dialog', { name: REPLACE, exact: true })).toBeHidden()
    await expect(shareLink(page)).toBeVisible()
  })

  for (const way of ['Cancel', 'Escape']) {
    // /ui/forms/cancel
    test(`${way} keeps the link instead of revoking it`, async ({ page, request }) => {
      await openSettings(page, request)
      const link = await createLink(page)

      const confirmation = await askToRevoke(page)
      if (way === 'Cancel') await confirmation.getByRole('button', { name: 'Cancel' }).click()
      else await page.keyboard.press('Escape')

      await expect(confirmation).toBeHidden()
      await page.reload()
      expect(await shownLink(page)).toBe(link)
    })
  }

  // /ui/errors/generic
  test('when Create fails: the generic error', async ({ page, request }) => {
    await openSettings(page, request)
    await page.route('**/settings/share-link', (route) => route.abort())

    await page.getByRole('button', { name: 'Create a share link' }).click()

    await expect(page.locator('main').getByText(GENERIC).filter({ visible: true })).toBeVisible()
    await expect(shareLink(page)).toHaveCount(0)
  })

  // /ui/forms/failure
  // /ui/errors/generic
  test('when Replace fails: the generic error in the confirmation', async ({ page, request }) => {
    await openSettings(page, request)
    await createLink(page)
    await page.route('**/settings/share-link', (route) => route.abort())

    const confirmation = await askToReplace(page)
    await confirmation.getByRole('button', { name: 'Replace', exact: true }).click()

    await expect(confirmation.getByText(GENERIC)).toBeVisible()
  })

  // /ui/forms/failure
  // /ui/errors/generic
  test('when Revoke fails: the generic error in the confirmation', async ({ page, request }) => {
    await openSettings(page, request)
    await createLink(page)
    await page.route('**/share-link/revoke', (route) => route.abort())

    const confirmation = await askToRevoke(page)
    await confirmation.getByRole('button', { name: 'Revoke', exact: true }).click()

    await expect(confirmation.getByText(GENERIC)).toBeVisible()
  })
})
