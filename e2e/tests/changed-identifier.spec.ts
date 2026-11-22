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
  datastarReady,
  addAbsence,
  nameInMenu,
  setPeriod,
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
  await datastarReady(other)
  await other
    .getByRole('button', { name: 'Change the association identifier', exact: true })
    .click()
  const dialog = other.getByRole('dialog', {
    name: 'Change the association identifier',
    exact: true,
  })
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
  return {
    slug,
    open: async () => {
      await page.goto(`/association/${slug}${screen}`)
      await datastarReady(page)
      if (header) await expect(page.locator('header').getByText(header)).toBeVisible()
    },
  }
}

function main(page: Page) {
  return page.locator('main')
}

test.describe('Changed identifier: Members', () => {
  // /ui/changed-identifier/actions
  test('Add a member from a screen opened before the change adds the member', async ({
    page,
    request,
  }) => {
    const { slug, open } = await openScreen(page, request, '/members', 'Members')
    await open()
    await changeIdentifierElsewhere(page, slug)

    await page.getByRole('button', { name: 'Add a member' }).click()
    const dialog = page.getByRole('dialog', { name: 'Add a member' })
    await dialog.getByLabel('Display name', { exact: true }).fill('Bruno')
    await dialog.getByLabel('Email', { exact: true }).fill(uniqueEmail('Bruno'))
    await dialog.getByRole('button', { name: 'Add member' }).click()

    await expect(page.getByText('Bruno added.')).toBeVisible()
    await expect(main(page).getByText(GENERIC).filter({ visible: true })).toHaveCount(0)
  })

  // /ui/changed-identifier/actions
  test('Rename from a screen opened before the change renames the association', async ({
    page,
    request,
  }) => {
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

    await page
      .getByRole('button', { name: 'Change the association identifier', exact: true })
      .click()
    const dialog = page.getByRole('dialog', {
      name: 'Change the association identifier',
      exact: true,
    })
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

    await page
      .getByRole('button', { name: 'Change the association identifier', exact: true })
      .click()
    const dialog = page.getByRole('dialog', {
      name: 'Change the association identifier',
      exact: true,
    })
    await dialog.getByLabel('Association identifier').fill(current)
    await dialog.getByRole('button', { name: 'Save' }).click()

    await expect(dialog).toBeHidden()
    await expect(page.getByText(/is now/)).toHaveCount(0)
    await expect(main(page).getByText(GENERIC).filter({ visible: true })).toHaveCount(0)
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
    await datastarReady(brunoPage)
    await expect(
      brunoPage.getByRole('button', { name: 'Delete the association', exact: true }),
    ).toBeVisible()
    const brunoId = await userIdOf(page.request, slug, 'Bruno')
    await page.request.post(`/association/${slug}/members/${brunoId}/role`, {
      data: { role: 'volunteer' },
    })
    await open()
    const current = await changeIdentifierElsewhere(page, slug)

    await brunoPage.getByRole('button', { name: 'Delete the association', exact: true }).click()
    const confirmation = brunoPage.getByRole('dialog', { name: /^Delete Jardin partagé\?/ })
    await confirmation.getByLabel("Type the association's name to confirm").fill(NAME)
    await confirmation.getByRole('button', { name: 'Delete', exact: true }).click()

    await expect(brunoPage).toHaveURL(new RegExp(`/association/${current}/members$`))
    await expect(
      brunoPage.getByRole('button', { name: 'Delete the association', exact: true }),
    ).toHaveCount(0)
    await expect(
      brunoPage.getByText('This association does not exist or you are not a member.'),
    ).toHaveCount(0)
    await brunoContext.close()
  })
})

test.describe('Changed identifier: Schedule settings', () => {
  // /ui/changed-identifier/actions
  test('Add a slot from a screen opened before the change adds the slot', async ({
    page,
    request,
  }) => {
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
    await expect(main(page).getByText(GENERIC).filter({ visible: true })).toHaveCount(0)
  })
})

test.describe('Changed identifier: My availability', () => {
  // /ui/changed-identifier/actions
  test('choosing a preference from a screen opened before the change saves it', async ({
    page,
    request,
  }) => {
    const { slug, open } = await openScreen(page, request, '/availability', 'My availability')
    await addSlot(page.request, slug, 'thursday', '10:00', '13:00')
    await open()
    const current = await changeIdentifierElsewhere(page, slug)

    await main(page).getByRole('combobox').selectOption({ label: 'Preferred' })

    await expect(main(page).getByText(GENERIC).filter({ visible: true })).toHaveCount(0)
    const other = await page.context().newPage()
    await expect(async () => {
      await other.goto(`/association/${current}/availability`)
      await datastarReady(other)
      await expect(
        other.locator('main').getByRole('combobox').locator('option:checked'),
      ).toHaveText('Preferred', {
        timeout: 1000,
      })
    }).toPass()
  })

  // /ui/changed-identifier/actions
  test('Add an absence from a screen opened before the change adds it', async ({
    page,
    request,
  }) => {
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
    await datastarReady(page)
    await expect(
      main(page)
        .getByRole('heading', { name: /^Week \d+$/ })
        .first(),
    ).toBeVisible()
    return slug
  }

  // /ui/changed-identifier/actions
  test('More weeks from a screen opened before the change adds four weeks', async ({
    page,
    request,
  }) => {
    const slug = await openSchedule(page, request)
    await changeIdentifierElsewhere(page, slug)

    await page.getByRole('button', { name: 'More weeks' }).click()

    await expect(main(page).getByRole('heading', { name: /^Week \d+$/ })).toHaveCount(10)
    await expect(main(page).getByText(GENERIC).filter({ visible: true })).toHaveCount(0)
  })

  // /ui/changed-identifier/actions
  test('Sign up from a screen opened before the change registers the user', async ({
    page,
    request,
  }) => {
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
  test('Confirm from a screen opened before the change confirms the registration', async ({
    page,
    request,
  }) => {
    await signedIn(page, request)
    const slug = await createAssociation(page.request, NAME)
    await addSlot(page.request, slug, 'thursday', '10:00', '13:00')
    const alice = await userIdOf(page.request, slug, 'Alice')
    const bruno = uniqueEmail('Bruno')
    await addMember(page.request, slug, 'Bruno', bruno, 'manager')
    await createAccount(request, 'Bruno', bruno)
    await propose(request, slug, alice, thursday(1).iso, '10:00', '13:00')
    await page.goto('/')
    await datastarReady(page)
    await expect(jardin(page)).toContainText('10:00–13:00 Alice ?')
    await changeIdentifierElsewhere(page, slug)

    await jardin(page).getByRole('button', { name: 'Confirm', exact: true }).click()

    await expect(jardin(page)).not.toContainText('?')
    await expect(jardin(page)).toContainText('10:00–13:00 Alice')
    await expect(jardin(page).getByRole('button', { name: 'Confirm', exact: true })).toHaveCount(0)
  })

  // /ui/changed-identifier/actions
  test('OK from a screen opened before the change cancels the obsolete registration', async ({
    page,
    request,
  }) => {
    await signedIn(page, request)
    const slug = await createAssociation(page.request, NAME)
    await addSlot(page.request, slug, 'thursday', '10:00', '13:00')
    await signUpFor(page.request, slug, thursday(1).iso, '10:00', '13:00')
    await addClosure(page.request, slug, thursday(1).iso, thursday(1).iso)
    await page.goto('/')
    await datastarReady(page)
    await expect(jardin(page)).toContainText('this slot no longer takes place.')
    await changeIdentifierElsewhere(page, slug)

    await jardin(page).getByRole('button', { name: 'OK', exact: true }).click()

    await expect(jardin(page)).not.toContainText('this slot no longer takes place.')
    await expect(jardin(page).getByRole('button', { name: 'OK', exact: true })).toHaveCount(0)
  })
})

test.describe('Changed identifier: Members, the edit dialog', () => {
  /** Alice opens Members, where Chloé volunteers, then another tab changes the identifier. */
  async function openMembers(page: Page, request: APIRequestContext, withLink = false) {
    const { slug, open } = await openScreen(page, request, '/members', 'Members')
    await addMember(page.request, slug, 'Chloé', uniqueEmail('Chloe'))
    if (withLink) {
      const chloe = await userIdOf(page.request, slug, 'Chloé')
      expect(
        (
          await page.request.post(`/association/${slug}/members/${chloe}/send-link`, { data: {} })
        ).status(),
      ).toBe(200)
    }
    await open()
    await changeIdentifierElsewhere(page, slug)
  }

  async function openEdit(page: Page) {
    await page.getByRole('button', { name: 'Edit Chloé', exact: true }).click()
    const dialog = page.getByRole('dialog', { name: 'Chloé', exact: true })
    await expect(dialog).toBeVisible()
    return dialog
  }

  async function confirm(page: Page, action: string, question: string, button: string) {
    const dialog = await openEdit(page)
    await dialog.getByRole('button', { name: action, exact: true }).click()
    const confirmation = page.getByRole('dialog', { name: question, exact: true })
    await confirmation.getByRole('button', { name: button, exact: true }).click()
  }

  // /ui/changed-identifier/actions
  test('Save with another role from a screen opened before the change changes the role', async ({
    page,
    request,
  }) => {
    await openMembers(page, request)

    const dialog = await openEdit(page)
    await dialog.getByRole('combobox', { name: /^Role/ }).selectOption({ label: 'Manager' })
    await dialog.getByRole('button', { name: 'Save' }).click()

    await expect(page.getByText('Chloé is now manager.')).toBeVisible()
    await expect(main(page).getByText(GENERIC).filter({ visible: true })).toHaveCount(0)
  })

  // /ui/changed-identifier/actions
  test('Remove from a screen opened before the change removes the member', async ({
    page,
    request,
  }) => {
    await openMembers(page, request)

    await confirm(
      page,
      'Remove from the association',
      'Remove Chloé from the association? Their upcoming registrations are cancelled.',
      'Remove',
    )

    await expect(page.getByText('Chloé is removed.')).toBeVisible()
    await expect(main(page).getByRole('listitem').filter({ hasText: 'Chloé' })).toHaveCount(0)
  })

  // /ui/changed-identifier/actions
  test('Send link from a screen opened before the change sends the link', async ({
    page,
    request,
  }) => {
    await openMembers(page, request)

    await confirm(page, 'Send link', "Send Chloé's sign-in link by email?", 'Send')

    await expect(page.getByText("Chloé's sign-in link is sent.")).toBeVisible()
    await expect(page.getByRole('dialog')).toHaveCount(0)
  })

  // /ui/changed-identifier/actions
  test('Revoke link from a screen opened before the change revokes the link', async ({
    page,
    request,
  }) => {
    await openMembers(page, request, true)

    await confirm(page, 'Revoke link', "Revoke Chloé's sign-in link?", 'Revoke')

    await expect(page.getByText("Chloé's sign-in link is revoked.")).toBeVisible()
    await expect(page.getByRole('dialog')).toHaveCount(0)
  })
})

test.describe('Changed identifier: Schedule settings, its dialogs', () => {
  const CLOSURE = 'Sat 14 Nov 2037'

  function section(page: Page, heading: string) {
    return main(page)
      .locator('section')
      .filter({ has: page.getByRole('heading', { name: heading, exact: true }) })
  }

  /** Alice opens Schedule settings, with the period and closure given, then another tab
   * changes the identifier. */
  async function openSettings(
    page: Page,
    request: APIRequestContext,
    setup: { period?: boolean; closure?: boolean; link?: boolean } = {},
  ) {
    const { slug, open } = await openScreen(page, request, '/settings', 'Schedule settings')
    if (setup.period) await setPeriod(page.request, slug, '2037-01-05', '2037-01-25')
    if (setup.closure) await addClosure(page.request, slug, '2037-11-14', '2037-11-14', 'Fête')
    if (setup.link) {
      expect(
        (
          await page.request.post(`/association/${slug}/settings/share-link`, { data: {} })
        ).status(),
      ).toBe(200)
    }
    await open()
    await changeIdentifierElsewhere(page, slug)
  }

  // /ui/changed-identifier/actions
  test('Save in "Planning period" from a screen opened before the change sets the period', async ({
    page,
    request,
  }) => {
    await openSettings(page, request)

    await page.getByRole('button', { name: 'Edit the period' }).click()
    const dialog = page.getByRole('dialog', { name: 'Planning period' })
    await dialog.getByLabel('From', { exact: true }).fill('2037-01-05')
    await dialog.getByLabel('To', { exact: true }).fill('2037-01-25')
    await dialog.getByRole('button', { name: 'Save' }).click()

    await expect(dialog).toBeHidden()
    await expect(section(page, 'Planning period')).toContainText('Mon 5 Jan 2037 – Sun 25 Jan 2037')
  })

  // /ui/changed-identifier/actions
  test('Clear from a screen opened before the change clears the period', async ({
    page,
    request,
  }) => {
    await openSettings(page, request, { period: true })

    await page.getByRole('button', { name: 'Clear the period' }).click()
    const confirmation = page.getByRole('dialog', {
      name: 'Clear the planning period?',
      exact: true,
    })
    await confirmation.getByRole('button', { name: 'Clear', exact: true }).click()

    await expect(confirmation).toBeHidden()
    await expect(section(page, 'Planning period').getByText('None', { exact: true })).toBeVisible()
  })

  // /ui/changed-identifier/actions
  test('Add a closure from a screen opened before the change adds it', async ({
    page,
    request,
  }) => {
    await openSettings(page, request)

    await page.getByRole('button', { name: 'Add a closure' }).click()
    const dialog = page.getByRole('dialog', { name: 'Add a closure' })
    await dialog.getByLabel('From', { exact: true }).fill('2037-11-14')
    await dialog.getByLabel('To', { exact: true }).fill('2037-11-14')
    await dialog.getByLabel('Label', { exact: true }).fill('Fête')
    await dialog.getByRole('button', { name: 'Add closure' }).click()

    await expect(dialog).toBeHidden()
    await expect(
      section(page, 'Closures').getByRole('listitem').filter({ hasText: CLOSURE }),
    ).toContainText('Fête')
  })

  // /ui/changed-identifier/actions
  test('Save in "Edit the closure" from a screen opened before the change changes it', async ({
    page,
    request,
  }) => {
    await openSettings(page, request, { closure: true })

    await section(page, 'Closures')
      .getByRole('listitem')
      .filter({ hasText: CLOSURE })
      .getByRole('button', { name: 'Edit the closure' })
      .click()
    const dialog = page.getByRole('dialog', { name: 'Edit the closure' })
    await dialog.getByLabel('Label', { exact: true }).fill('Kermesse')
    await dialog.getByRole('button', { name: 'Save' }).click()

    await expect(dialog).toBeHidden()
    await expect(
      section(page, 'Closures').getByRole('listitem').filter({ hasText: CLOSURE }),
    ).toContainText('Kermesse')
  })

  // /ui/changed-identifier/actions
  test('Delete the closure from a screen opened before the change deletes it', async ({
    page,
    request,
  }) => {
    await openSettings(page, request, { closure: true })

    await section(page, 'Closures')
      .getByRole('listitem')
      .filter({ hasText: CLOSURE })
      .getByRole('button', { name: 'Delete the closure' })
      .click()
    const confirmation = page.getByRole('dialog', { name: /^Delete the closure "Fête"\?/ })
    await confirmation.getByRole('button', { name: 'Delete', exact: true }).click()

    await expect(confirmation).toBeHidden()
    await expect(section(page, 'Closures').getByText('None', { exact: true })).toBeVisible()
  })

  // /ui/changed-identifier/actions
  test('Create a share link from a screen opened before the change creates it', async ({
    page,
    request,
  }) => {
    await openSettings(page, request)

    await page.getByRole('button', { name: 'Create a share link' }).click()

    await expect(section(page, 'Share link').getByText(/\/shared\/[\w-]+/)).toBeVisible()
    await expect(main(page).getByText(GENERIC).filter({ visible: true })).toHaveCount(0)
  })

  // /ui/changed-identifier/actions
  test('Revoke the share link from a screen opened before the change revokes it', async ({
    page,
    request,
  }) => {
    await openSettings(page, request, { link: true })

    await page.getByRole('button', { name: 'Revoke the share link' }).click()
    const confirmation = page.getByRole('dialog', {
      name: 'Revoke the share link? It no longer shows the Schedule.',
      exact: true,
    })
    await confirmation.getByRole('button', { name: 'Revoke', exact: true }).click()

    await expect(confirmation).toBeHidden()
    await expect(section(page, 'Share link').getByText('None', { exact: true })).toBeVisible()
  })
})

test.describe('Changed identifier: My availability, an absence', () => {
  const ABSENCE = 'Mon 9 Nov 2037 – Sun 15 Nov 2037'

  async function openAbsence(page: Page, request: APIRequestContext) {
    const { slug, open } = await openScreen(page, request, '/availability', 'My availability')
    await addAbsence(page.request, slug, '2037-11-09', '2037-11-15')
    await open()
    await changeIdentifierElsewhere(page, slug)
    return main(page).getByRole('listitem').filter({ hasText: ABSENCE })
  }

  // /ui/changed-identifier/actions
  test('Save in "Edit the absence" from a screen opened before the change changes it', async ({
    page,
    request,
  }) => {
    const line = await openAbsence(page, request)

    await line.getByRole('button', { name: 'Edit the absence' }).click()
    const dialog = page.getByRole('dialog', { name: 'Edit the absence' })
    await dialog.getByLabel('To', { exact: true }).fill('2037-11-20')
    await dialog.getByRole('button', { name: 'Save' }).click()

    await expect(dialog).toBeHidden()
    await expect(
      main(page).getByRole('listitem').filter({ hasText: 'Mon 9 Nov 2037 – Fri 20 Nov 2037' }),
    ).toHaveCount(1)
  })

  // /ui/changed-identifier/actions
  test('Delete the absence from a screen opened before the change deletes it', async ({
    page,
    request,
  }) => {
    const line = await openAbsence(page, request)

    await line.getByRole('button', { name: 'Delete the absence' }).click()
    const confirmation = page.getByRole('dialog', {
      name: `Delete the absence of ${ABSENCE}?`,
      exact: true,
    })
    await confirmation.getByRole('button', { name: 'Delete', exact: true }).click()

    await expect(confirmation).toBeHidden()
    await expect(line).toHaveCount(0)
  })
})

test.describe('Changed identifier: Schedule, the menu', () => {
  // /ui/changed-identifier/actions
  test("a member's name from a screen opened before the change proposes the slot", async ({
    page,
    request,
  }) => {
    const { slug } = await openScreen(page, request, '')
    await addSlot(page.request, slug, 'thursday', '10:00', '13:00')
    await addMember(page.request, slug, 'Bruno', uniqueEmail('Bruno'))
    await page.goto(`/association/${slug}`)
    await datastarReady(page)
    await changeIdentifierElsewhere(page, slug)
    const day = page.getByRole('group', { name: thursday(2).label, exact: true })

    await day.getByRole('listitem').click()
    await nameInMenu(page, 'Bruno').click()

    await expect(day.getByRole('listitem')).toHaveText('Bruno ?')
  })

  // /ui/changed-identifier/actions
  test('"Yes, cancel" from a screen opened before the change cancels the registration', async ({
    page,
    request,
  }) => {
    const { slug } = await openScreen(page, request, '')
    await addSlot(page.request, slug, 'thursday', '10:00', '13:00')
    await signUpFor(page.request, slug, thursday(2).iso, '10:00', '13:00')
    await page.goto(`/association/${slug}`)
    await datastarReady(page)
    await changeIdentifierElsewhere(page, slug)
    const day = page.getByRole('group', { name: thursday(2).label, exact: true })

    await day.getByRole('listitem').click()
    await page.getByRole('button', { name: 'Cancel registration…' }).click()
    const dialog = page.getByRole('dialog').filter({ hasText: 'Cancel this registration?' })
    await dialog.getByRole('button', { name: 'Yes, cancel' }).click()

    await expect(dialog).toBeHidden()
    await expect(day.getByRole('listitem').locator('s')).toHaveText('Alice')
  })
})

test.describe('Changed identifier: Schedule settings, a slot and a preference', () => {
  /** Alice opens Schedule settings with a Thursday slot and Bruno as volunteer, then another tab
   * changes the identifier. */
  async function openSettings(page: Page, request: APIRequestContext) {
    const { slug, open } = await openScreen(page, request, '/settings', 'Schedule settings')
    await addSlot(page.request, slug, 'thursday', '10:00', '13:00')
    await addMember(page.request, slug, 'Bruno', uniqueEmail('Bruno'))
    await open()
    return changeIdentifierElsewhere(page, slug)
  }

  function slots(page: Page) {
    return main(page)
      .locator('section')
      .filter({ has: page.getByRole('heading', { name: 'Slots', exact: true }) })
  }

  // /ui/changed-identifier/actions
  test('Save in "Edit the slot" from a screen opened before the change changes it', async ({
    page,
    request,
  }) => {
    await openSettings(page, request)

    await slots(page)
      .getByRole('listitem')
      .filter({ hasText: 'Thursday' })
      .getByRole('button', { name: 'Edit the slot' })
      .click()
    const dialog = page.getByRole('dialog', { name: 'Edit the slot' })
    await dialog.getByLabel('Day').selectOption({ label: 'Friday' })
    await dialog.getByRole('button', { name: 'Save' }).click()

    await expect(dialog).toBeHidden()
    await expect(slots(page).getByRole('listitem').filter({ hasText: 'Friday' })).toHaveCount(1)
    await expect(slots(page).getByRole('listitem').filter({ hasText: 'Thursday' })).toHaveCount(0)
  })

  // /ui/changed-identifier/actions
  test('Delete the slot from a screen opened before the change deletes it', async ({
    page,
    request,
  }) => {
    await openSettings(page, request)

    await slots(page)
      .getByRole('listitem')
      .filter({ hasText: 'Thursday' })
      .getByRole('button', { name: 'Delete the slot' })
      .click()
    const confirmation = page.getByRole('dialog', {
      name: /^Delete the slot Thursday 10:00–13:00\?/,
    })
    await confirmation.getByRole('button', { name: 'Delete', exact: true }).click()

    await expect(confirmation).toBeHidden()
    await expect(slots(page).getByText('None', { exact: true })).toBeVisible()
  })

  // /ui/changed-identifier/actions
  test("a member's preference from a screen opened before the change saves it", async ({
    page,
    request,
  }) => {
    const current = await openSettings(page, request)
    const cell = (on: Page) =>
      on
        .locator('main section')
        .filter({ has: on.getByRole('heading', { name: "Members' preferences" }) })
        .getByRole('row')
        .filter({ hasText: 'Bruno' })
        .getByRole('combobox')

    await cell(page).selectOption({ label: 'Unavailable' })

    await expect(main(page).getByText(GENERIC).filter({ visible: true })).toHaveCount(0)
    const other = await page.context().newPage()
    await expect(async () => {
      await other.goto(`/association/${current}/settings`)
      await datastarReady(other)
      await expect(cell(other)).toHaveValue('unavailable', { timeout: 1000 })
    }).toPass()
  })
})

test.describe('Changed identifier: My availability, the note', () => {
  // /ui/changed-identifier/actions
  test('Save in "Note for the managers" from a screen opened before the change saves it', async ({
    page,
    request,
  }) => {
    const { slug, open } = await openScreen(page, request, '/availability', 'My availability')
    await open()
    await changeIdentifierElsewhere(page, slug)

    await page.getByRole('button', { name: 'Edit the note' }).click()
    const dialog = page.getByRole('dialog', { name: 'Note for the managers' })
    await dialog.getByLabel('Text', { exact: true }).fill('Mornings only.')
    await dialog.getByRole('button', { name: 'Save' }).click()

    await expect(dialog).toBeHidden()
    await expect(
      main(page).getByText('Mornings only.', { exact: true }).filter({ visible: true }),
    ).toBeVisible()
  })
})

test.describe('Changed identifier: Schedule, Confirm', () => {
  // /ui/changed-identifier/actions
  test('Confirm in the menu from a screen opened before the change confirms the registration', async ({
    page,
    request,
  }) => {
    const { slug } = await openScreen(page, request, '')
    await addSlot(page.request, slug, 'thursday', '10:00', '13:00')
    await addMember(page.request, slug, 'Bruno', uniqueEmail('Bruno'))
    const bruno = await userIdOf(page.request, slug, 'Bruno')
    await propose(page.request, slug, bruno, thursday(2).iso, '10:00', '13:00')
    await page.goto(`/association/${slug}`)
    await datastarReady(page)
    await changeIdentifierElsewhere(page, slug)
    const day = page.getByRole('group', { name: thursday(2).label, exact: true })
    await expect(day.getByRole('listitem')).toHaveText('Bruno ?')

    await day.getByRole('listitem').click()
    await page
      .locator('#occurrence-menu')
      .getByRole('button', { name: 'Confirm', exact: true })
      .click()

    await expect(day.getByRole('listitem')).toHaveText('Bruno')
  })
})
