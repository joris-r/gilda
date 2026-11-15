import { expect, test, type APIRequestContext, type Page } from '@playwright/test'
import {
  addMember,
  addSlot,
  createAccount,
  createAssociation,
  propose,
  signUpFor,
  addClosure,
  signedIn,
  uniqueEmail,
  uniqueSlug,
  userIdOf,
} from './helpers'

const NAME = 'Jardin partagé'
const GENERIC = 'Something went wrong. Try again.'
const WEEKDAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

/** A Thursday `weeksAhead` weeks after the current week, as an ISO date and as the Schedule labels it. */
function thursday(weeksAhead: number) {
  const day = new Date()
  day.setHours(12, 0, 0, 0)
  day.setDate(day.getDate() - ((day.getDay() + 6) % 7) + 7 * weeksAhead + 3)
  const iso = `${day.getFullYear()}-${String(day.getMonth() + 1).padStart(2, '0')}-${String(day.getDate()).padStart(2, '0')}`
  return { iso, label: `${WEEKDAYS[day.getDay()]} ${day.getDate()} ${MONTHS[day.getMonth()]}` }
}

/** Another tab of the association's manager changes its identifier, as Members does, and the
 * `page` already open keeps showing the former one; returns the new identifier. */
async function changeIdentifierElsewhere(page: Page, slug: string) {
  const changed = uniqueSlug()
  const other = await page.context().newPage()
  await other.goto(`/association/${slug}/members`)
  await other.getByRole('button', { name: 'Change the association identifier', exact: true }).click()
  const dialog = other.getByRole('dialog', { name: 'Change the association identifier', exact: true })
  await dialog.getByLabel('Association identifier').fill(changed)
  await dialog.getByRole('button', { name: 'Save' }).click()
  await expect(other).toHaveURL(new RegExp(`/association/${changed}/members$`))
  await other.close()
  return changed
}

/** Alice signs in on `page`, creates an association and opens `screen` of it; returns its slug. */
async function openScreen(page: Page, request: APIRequestContext, screen: string, header?: string) {
  await signedIn(page, request)
  const slug = await createAssociation(page.request, NAME)
  return { slug, open: async () => {
    await page.goto(`/association/${slug}${screen}`)
    if (header) await expect(page.locator('header').getByText(header)).toBeVisible()
  } }
}

function main(page: Page) {
  return page.locator('main')
}

test.describe('Changed identifier: Members', () => {
  // /ui/changed-identifier/actions
  test('Add a member from a screen opened before the change adds the member', async ({ page, request }) => {
    const { slug, open } = await openScreen(page, request, '/members', 'Members')
    await open()
    await changeIdentifierElsewhere(page, slug)

    await page.getByRole('button', { name: 'Add a member' }).click()
    const dialog = page.getByRole('dialog', { name: 'Add a member' })
    await dialog.getByLabel('Display name', { exact: true }).fill('Bruno')
    await dialog.getByLabel('Email', { exact: true }).fill(uniqueEmail('Bruno'))
    await dialog.getByRole('button', { name: 'Add member' }).click()

    await expect(page.getByText('Bruno added.')).toBeVisible()
    await expect(main(page).getByText(GENERIC)).toHaveCount(0)
  })

  // /ui/changed-identifier/actions
  test('Rename from a screen opened before the change renames the association', async ({ page, request }) => {
    const { slug, open } = await openScreen(page, request, '/members', 'Members')
    await open()
    await changeIdentifierElsewhere(page, slug)

    await page.getByRole('button', { name: 'Rename the association', exact: true }).click()
    const dialog = page.getByRole('dialog', { name: 'Rename the association', exact: true })
    await dialog.getByLabel('Name', { exact: true }).fill('Les Lilas')
    await dialog.getByRole('button', { name: 'Save' }).click()

    await expect(page.getByText('The association is now Les Lilas.')).toBeVisible()
    await expect(page.getByRole('dialog')).toHaveCount(0)
  })

  // /ui/changed-identifier/actions
  test('Save with another identifier from a screen opened before the change moves to its URL', async ({
    page,
    request,
  }) => {
    const { slug, open } = await openScreen(page, request, '/members', 'Members')
    await open()
    await changeIdentifierElsewhere(page, slug)
    const next = uniqueSlug()

    await page.getByRole('button', { name: 'Change the association identifier', exact: true }).click()
    const dialog = page.getByRole('dialog', { name: 'Change the association identifier', exact: true })
    await dialog.getByLabel('Association identifier').fill(next)
    await dialog.getByRole('button', { name: 'Save' }).click()

    await expect(page).toHaveURL(new RegExp(`/association/${next}/members$`))
    await expect(page.getByText(`The association identifier is now ${next}.`)).toBeVisible()
  })

  // /ui/changed-identifier/actions
  // /core/ui/members/same-slug
  test('Save with the current identifier from a screen opened before the change closes the dialog and says nothing', async ({
    page,
    request,
  }) => {
    const { slug, open } = await openScreen(page, request, '/members', 'Members')
    await open()
    const current = await changeIdentifierElsewhere(page, slug)

    await page.getByRole('button', { name: 'Change the association identifier', exact: true }).click()
    const dialog = page.getByRole('dialog', { name: 'Change the association identifier', exact: true })
    await dialog.getByLabel('Association identifier').fill(current)
    await dialog.getByRole('button', { name: 'Save' }).click()

    await expect(dialog).toBeHidden()
    await expect(page.getByText(/is now/)).toHaveCount(0)
    await expect(main(page).getByText(GENERIC)).toHaveCount(0)
  })

  // /ui/changed-identifier/actions
  test('Delete from a screen opened before the change deletes the association and leads to My associations', async ({
    page,
    request,
  }) => {
    const { slug, open } = await openScreen(page, request, '/members', 'Members')
    await open()
    await changeIdentifierElsewhere(page, slug)

    await page.getByRole('button', { name: 'Delete the association', exact: true }).click()
    const confirmation = page.getByRole('dialog', { name: /^Delete Jardin partagé\?/ })
    await confirmation.getByLabel("Type the association's name to confirm").fill(NAME)
    await confirmation.getByRole('button', { name: 'Delete', exact: true }).click()

    await expect(page).toHaveURL(/\/$/)
    await expect(page.getByText(`${NAME} is deleted.`)).toBeVisible()
  })

  // /ui/changed-identifier/actions
  // /core/ui/members/delete-refused
  test('a refused Delete from a screen opened before the change shows Members at its current URL', async ({
    page,
    request,
    browser,
  }) => {
    const { slug, open } = await openScreen(page, request, '/members', 'Members')
    const bruno = uniqueEmail('Bruno')
    await addMember(page.request, slug, 'Bruno', bruno, 'manager')
    const brunoContext = await browser.newContext()
    const brunoPage = await brunoContext.newPage()
    await createAccount(brunoContext.request, 'Bruno', bruno)
    await brunoPage.goto(`/association/${slug}/members`)
    await expect(brunoPage.getByRole('button', { name: 'Delete the association', exact: true })).toBeVisible()
    const brunoId = await userIdOf(page.request, slug, 'Bruno')
    await page.request.post(`/association/${slug}/members/${brunoId}/role`, { data: { role: 'volunteer' } })
    await open()
    const current = await changeIdentifierElsewhere(page, slug)

    await brunoPage.getByRole('button', { name: 'Delete the association', exact: true }).click()
    const confirmation = brunoPage.getByRole('dialog', { name: /^Delete Jardin partagé\?/ })
    await confirmation.getByLabel("Type the association's name to confirm").fill(NAME)
    await confirmation.getByRole('button', { name: 'Delete', exact: true }).click()

    await expect(brunoPage).toHaveURL(new RegExp(`/association/${current}/members$`))
    await expect(brunoPage.getByRole('button', { name: 'Delete the association', exact: true })).toHaveCount(0)
    await expect(brunoPage.getByText('This association does not exist or you are not a member.')).toHaveCount(0)
    await brunoContext.close()
  })
})

test.describe('Changed identifier: Schedule settings', () => {
  // /ui/changed-identifier/actions
  test('Add a slot from a screen opened before the change adds the slot', async ({ page, request }) => {
    const { slug, open } = await openScreen(page, request, '/settings', 'Schedule settings')
    await open()
    await changeIdentifierElsewhere(page, slug)

    await page.getByRole('button', { name: 'Add a slot' }).click()
    const dialog = page.getByRole('dialog', { name: 'Add a slot' })
    await dialog.getByLabel('Day').selectOption({ label: 'Thursday' })
    await dialog.getByLabel('From', { exact: true }).fill('10:00')
    await dialog.getByLabel('To', { exact: true }).fill('13:00')
    await dialog.getByRole('button', { name: 'Add slot' }).click()

    await expect(dialog).toBeHidden()
    await expect(main(page).getByRole('listitem').filter({ hasText: 'Thursday' })).toHaveCount(1)
    await expect(main(page).getByText(GENERIC)).toHaveCount(0)
  })
})

test.describe('Changed identifier: My availability', () => {
  // /ui/changed-identifier/actions
  test('choosing a preference from a screen opened before the change saves it', async ({ page, request }) => {
    const { slug, open } = await openScreen(page, request, '/availability', 'My availability')
    await addSlot(page.request, slug, 'thursday', '10:00', '13:00')
    await open()
    const current = await changeIdentifierElsewhere(page, slug)

    await main(page).getByRole('combobox').selectOption({ label: 'Preferred' })

    await expect(main(page).getByText(GENERIC)).toHaveCount(0)
    await page.goto(`/association/${current}/availability`)
    await expect(main(page).getByRole('combobox').locator('option:checked')).toHaveText('Preferred')
  })

  // /ui/changed-identifier/actions
  test('Add an absence from a screen opened before the change adds it', async ({ page, request }) => {
    const { slug, open } = await openScreen(page, request, '/availability', 'My availability')
    await open()
    await changeIdentifierElsewhere(page, slug)

    await page.getByRole('button', { name: 'Add an absence' }).click()
    const dialog = page.getByRole('dialog', { name: 'Add an absence' })
    await dialog.getByLabel('From', { exact: true }).fill('2037-11-09')
    await dialog.getByLabel('To', { exact: true }).fill('2037-11-15')
    await dialog.getByRole('button', { name: 'Add absence' }).click()

    await expect(dialog).toBeHidden()
    await expect(main(page).getByRole('listitem').filter({ hasText: '2037' })).toHaveCount(1)
  })
})

test.describe('Changed identifier: Schedule', () => {
  async function openSchedule(page: Page, request: APIRequestContext) {
    const { slug } = await openScreen(page, request, '')
    await addSlot(page.request, slug, 'thursday', '10:00', '13:00')
    await signUpFor(page.request, slug, thursday(1).iso, '10:00', '13:00')
    await page.goto(`/association/${slug}`)
    await expect(main(page).getByRole('heading', { name: /^Week \d+$/ }).first()).toBeVisible()
    return slug
  }

  // /ui/changed-identifier/actions
  test('More weeks from a screen opened before the change adds four weeks', async ({ page, request }) => {
    const slug = await openSchedule(page, request)
    await changeIdentifierElsewhere(page, slug)

    await page.getByRole('button', { name: 'More weeks' }).click()

    await expect(main(page).getByRole('heading', { name: /^Week \d+$/ })).toHaveCount(10)
    await expect(main(page).getByText(GENERIC)).toHaveCount(0)
  })

  // /ui/changed-identifier/actions
  test('Sign up from a screen opened before the change registers the user', async ({ page, request }) => {
    const slug = await openSchedule(page, request)
    await changeIdentifierElsewhere(page, slug)
    const day = page.getByRole('group', { name: thursday(2).label, exact: true })

    await day.getByRole('listitem').click()
    await page.getByRole('button', { name: 'Sign up' }).click()

    await expect(day.getByRole('listitem')).toHaveText('Alice')
  })
})

test.describe('Changed identifier: My associations', () => {
  function jardin(page: Page) {
    return main(page).getByRole('listitem').filter({ hasText: NAME })
  }

  // /ui/changed-identifier/actions
  test('Confirm from a screen opened before the change confirms the registration', async ({ page, request }) => {
    await signedIn(page, request)
    const slug = await createAssociation(page.request, NAME)
    await addSlot(page.request, slug, 'thursday', '10:00', '13:00')
    const alice = await userIdOf(page.request, slug, 'Alice')
    const bruno = uniqueEmail('Bruno')
    await addMember(page.request, slug, 'Bruno', bruno, 'manager')
    await createAccount(request, 'Bruno', bruno)
    await propose(request, slug, alice, thursday(1).iso, '10:00', '13:00')
    await page.goto('/')
    await expect(jardin(page)).toContainText('10:00–13:00 Alice ?')
    await changeIdentifierElsewhere(page, slug)

    await jardin(page).getByRole('button', { name: 'Confirm', exact: true }).click()

    await expect(jardin(page)).not.toContainText('?')
    await expect(jardin(page)).toContainText('10:00–13:00 Alice')
    await expect(jardin(page).getByRole('button', { name: 'Confirm', exact: true })).toHaveCount(0)
  })

  // /ui/changed-identifier/actions
  test('OK from a screen opened before the change cancels the obsolete registration', async ({ page, request }) => {
    await signedIn(page, request)
    const slug = await createAssociation(page.request, NAME)
    await addSlot(page.request, slug, 'thursday', '10:00', '13:00')
    await signUpFor(page.request, slug, thursday(1).iso, '10:00', '13:00')
    await addClosure(page.request, slug, thursday(1).iso, thursday(1).iso)
    await page.goto('/')
    await expect(jardin(page)).toContainText('this slot no longer takes place.')
    await changeIdentifierElsewhere(page, slug)

    await jardin(page).getByRole('button', { name: 'OK', exact: true }).click()

    await expect(jardin(page)).not.toContainText('this slot no longer takes place.')
    await expect(jardin(page).getByRole('button', { name: 'OK', exact: true })).toHaveCount(0)
  })
})
