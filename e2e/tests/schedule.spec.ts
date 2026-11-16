import { expect, test, type APIRequestContext, type Page } from '@playwright/test'
import {
  addAbsence,
  addMember,
  addSlot,
  createAccount,
  createAssociation,
  saveNote,
  signUpFor,
  propose,
  signedIn,
  signIn,
  uniqueEmail,
  userIdOf,
  datastarReady,
} from './helpers'

const GENERIC = 'Something went wrong. Try again.'
const TAKEN = 'Someone took this slot in the meantime.'
const WEEKDAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

/** A day of the week `weeksAhead` weeks after the current one (0 = Sunday … 6 = Saturday). */
function dayOfWeek(weekday: number, weeksAhead: number) {
  const day = new Date()
  day.setHours(12, 0, 0, 0)
  day.setDate(day.getDate() - ((day.getDay() + 6) % 7) + 7 * weeksAhead + ((weekday + 6) % 7))
  const iso = `${day.getFullYear()}-${String(day.getMonth() + 1).padStart(2, '0')}-${String(day.getDate()).padStart(2, '0')}`
  return {
    iso,
    label: `${WEEKDAYS[day.getDay()]} ${day.getDate()} ${MONTHS[day.getMonth()]}`,
  }
}

/** Alice signs in on `page`, creates an association open on Thursdays from 10:00 to 13:00, signs
 * up for next week's Thursday, and opens its Schedule. */
async function openSchedule(page: Page, request: APIRequestContext) {
  await signedIn(page, request)
  const slug = await createAssociation(page.request)
  await addSlot(page.request, slug, 'thursday', '10:00', '13:00')
  await signUpFor(page.request, slug, dayOfWeek(4, 1).iso, '10:00', '13:00')
  await page.goto(`/association/${slug}`)
  await datastarReady(page)
  await expect(page.locator('main').getByRole('heading', { name: /^Week \d+$/ }).first()).toBeVisible()
  return slug
}

function weekHeadings(page: Page) {
  return page.locator('main').getByRole('heading', { name: /^Week \d+$/ })
}

test.describe('Schedule', () => {
  for (const [screen, rest] of [
    ['My availability', 'availability'],
    ['Members', 'members'],
    ['Schedule settings', 'settings'],
  ]) {
    // /planning/ui/schedule/links
    test(`"${screen}" leads to that screen`, async ({ page, request }) => {
      const slug = await openSchedule(page, request)

      await page.getByRole('link', { name: screen, exact: true }).click()

      await expect(page).toHaveURL(new RegExp(`/association/${slug}/${rest}$`))
      await expect(page.locator('header').getByText(screen)).toBeVisible()
    })
  }

  // /planning/ui/schedule/more
  test('"More weeks", at the end, adds four more', async ({ page, request }) => {
    await openSchedule(page, request)
    const last = await weekHeadings(page).last().textContent()

    await page.getByRole('button', { name: 'More weeks' }).click()

    await expect(weekHeadings(page)).toHaveCount(10)
    await expect(weekHeadings(page).nth(6)).not.toHaveText(last ?? '')
    await expect(page.getByRole('group', { name: dayOfWeek(4, 8).label, exact: true })).toBeVisible()
  })

  // /planning/ui/schedule/more
  test('"More weeks" adds four more each time', async ({ page, request }) => {
    await openSchedule(page, request)

    await page.getByRole('button', { name: 'More weeks' }).click()
    await expect(weekHeadings(page)).toHaveCount(10)
    await page.getByRole('button', { name: 'More weeks' }).click()

    await expect(weekHeadings(page)).toHaveCount(14)
    await expect(page.getByRole('group', { name: dayOfWeek(4, 12).label, exact: true })).toBeVisible()
  })

  // /planning/ui/schedule/more
  test('the weeks added keep the occurrences shown', async ({ page, request }) => {
    await openSchedule(page, request)

    await page.getByRole('button', { name: 'More weeks' }).click()

    await expect(weekHeadings(page)).toHaveCount(10)
    const day = page.getByRole('group', { name: dayOfWeek(4, 1).label, exact: true })
    await expect(day.getByRole('listitem')).toHaveText('Alice')
  })

  // /ui/errors/generic
  test('"More weeks" when the server fails: the generic error', async ({ page, request }) => {
    await openSchedule(page, request)
    await page.route('**/weeks', (route) => route.fulfill({ status: 500, body: 'failure' }))

    await page.getByRole('button', { name: 'More weeks' }).click()

    await expect(page.locator('main').getByText(GENERIC).filter({ visible: true })).toBeVisible()
    await expect(weekHeadings(page)).toHaveCount(6)
  })
})

function dayGroup(page: Page, weeksAhead: number) {
  return page.getByRole('group', { name: dayOfWeek(4, weeksAhead).label, exact: true })
}

function menuTitle(page: Page, weeksAhead: number) {
  return page.getByText(`${dayOfWeek(4, weeksAhead).label} · 10–13`, { exact: true })
}

test.describe('Schedule menu', () => {

  // /planning/ui/schedule/menu
  test('clicking an occurrence before today opens nothing', async ({ page, request }) => {
    await openSchedule(page, request)

    await dayGroup(page, -1).getByRole('listitem').click()

    await expect(menuTitle(page, -1)).toBeHidden()
    await expect(page.getByRole('button', { name: 'Sign up' })).toBeHidden()
  })

  // /planning/ui/occurrence-menu/escape
  test('Escape closes the menu', async ({ page, request }) => {
    await openSchedule(page, request)
    await dayGroup(page, 2).getByRole('listitem').click()
    await expect(menuTitle(page, 2)).toBeVisible()

    await page.keyboard.press('Escape')

    await expect(menuTitle(page, 2)).toBeHidden()
  })

  // /planning/ui/occurrence-menu/sign-up
  // /planning/ui/occurrence-menu/closes
  // /planning/operations/register/self
  test('"Sign up" closes the menu and the occurrence shows the user', async ({ page, request }) => {
    await openSchedule(page, request)
    await dayGroup(page, 2).getByRole('listitem').click()

    await page.getByRole('button', { name: 'Sign up' }).click()

    await expect(dayGroup(page, 2).getByRole('listitem')).toHaveText('Alice')
    await expect(menuTitle(page, 2)).toBeHidden()
    await page.reload()
    await datastarReady(page)
    await expect(dayGroup(page, 2).getByRole('listitem')).toHaveText('Alice')
  })

  // /planning/ui/occurrence-menu/closes
  test('"Sign up" keeps the weeks shown', async ({ page, request }) => {
    await openSchedule(page, request)
    await page.getByRole('button', { name: 'More weeks' }).click()
    await expect(weekHeadings(page)).toHaveCount(10)
    await dayGroup(page, 8).getByRole('listitem').click()

    await page.getByRole('button', { name: 'Sign up' }).click()

    await expect(dayGroup(page, 8).getByRole('listitem')).toHaveText('Alice')
    await expect(weekHeadings(page)).toHaveCount(10)
  })

  // /ui/errors/generic
  test('"Sign up" when the server fails: the generic error, and the menu stays', async ({ page, request }) => {
    await openSchedule(page, request)
    await page.route('**/sign-up', (route) => route.fulfill({ status: 500, body: 'failure' }))
    await dayGroup(page, 2).getByRole('listitem').click()

    await page.getByRole('button', { name: 'Sign up' }).click()

    await expect(page.getByText(GENERIC).filter({ visible: true })).toBeVisible()
    await expect(menuTitle(page, 2)).toBeVisible()
    await expect(dayGroup(page, 2).getByRole('listitem')).toHaveText('')
  })

  // /planning/ui/occurrence-menu/cancel
  // /planning/ui/occurrence-menu/cancel-registration
  test('"Cancel registration…" asks first; "Keep it" changes nothing', async ({ page, request }) => {
    await openSchedule(page, request)
    await dayGroup(page, 1).getByRole('listitem').click()

    await page.getByRole('button', { name: 'Cancel registration…' }).click()
    const dialog = page.getByRole('dialog').filter({ hasText: 'Cancel this registration?' })
    await expect(dialog).toBeVisible()
    await dialog.getByRole('button', { name: 'Keep it' }).click()

    await expect(dialog).toBeHidden()
    await page.reload()
    await datastarReady(page)
    await dayGroup(page, 1).getByRole('listitem').click()
    await expect(page.getByRole('button', { name: 'Cancel registration…' })).toBeVisible()
  })

  // /planning/ui/occurrence-menu/cancel-registration
  // /planning/operations/change-registration/cancel
  // /planning/ui/occurrence-menu/free
  test('"Yes, cancel" cancels the registration and closes the dialog', async ({ page, request }) => {
    await openSchedule(page, request)
    await dayGroup(page, 1).getByRole('listitem').click()

    await page.getByRole('button', { name: 'Cancel registration…' }).click()
    const dialog = page.getByRole('dialog').filter({ hasText: 'Cancel this registration?' })
    await dialog.getByRole('button', { name: 'Yes, cancel' }).click()

    await expect(dialog).toBeHidden()
    await expect(menuTitle(page, 1)).toBeHidden()
    await dayGroup(page, 1).getByRole('listitem').click()
    await expect(page.getByRole('button', { name: 'Sign up' })).toBeVisible()
  })
})

const NOTE = 'Always group my registrations in pairs.'

/** The Schedule's menu, wherever it is open. */
function menu(page: Page) {
  return page.locator('#occurrence-menu')
}

/** The Schedule of `openSchedule`, where Bruno also volunteers, and Alice is absent the whole
 * week two weeks ahead, with a note for the managers. */
async function openManagersSchedule(page: Page, request: APIRequestContext) {
  const slug = await openSchedule(page, request)
  await addMember(page.request, slug, 'Bruno', uniqueEmail('Bruno'))
  await addAbsence(page.request, slug, dayOfWeek(1, 2).iso, dayOfWeek(0, 2).iso)
  await saveNote(page.request, slug, NOTE)
  await page.reload()
  await datastarReady(page)
  await expect(weekHeadings(page).first()).toBeVisible()
  return slug
}

/** The text of Alice's absence icon: the week two weeks ahead, from Monday to Sunday. */
function absenceText() {
  const monday = dayOfWeek(1, 2)
  const sunday = dayOfWeek(0, 2)
  return `Absent ${monday.label} ${monday.iso.slice(0, 4)} – ${sunday.label} ${sunday.iso.slice(0, 4)}`
}

/** The Schedule of `openSchedule`, opened by Bruno, a volunteer, Alice holding next week's
 * Thursday. */
async function openVolunteersSchedule(page: Page, request: APIRequestContext) {
  const slug = await openSchedule(page, request)
  const email = uniqueEmail('Bruno')
  await addMember(page.request, slug, 'Bruno', email)
  await createAccount(request, 'Bruno', email)
  await page.context().clearCookies()
  await signIn(page, email)
  await page.goto(`/association/${slug}`)
  await datastarReady(page)
  await expect(weekHeadings(page).first()).toBeVisible()
  return slug
}

test.describe('Schedule menu: taking over a slot', () => {
  // /planning/ui/occurrence-menu/take-over-ask
  test('"Take over this slot…" asks first; "Keep it" changes nothing', async ({ page, request }) => {
    await openVolunteersSchedule(page, request)
    await dayGroup(page, 1).getByRole('listitem').click()

    await menu(page).getByRole('button', { name: 'Take over this slot…' }).click()
    const dialog = page.getByRole('dialog').filter({ hasText: 'Take this slot from Alice?' })
    await expect(dialog).toBeVisible()
    await dialog.getByRole('button', { name: 'Keep it' }).click()

    await expect(dialog).toBeHidden()
    await page.reload()
    await datastarReady(page)
    await expect(dayGroup(page, 1).getByRole('listitem')).toHaveText('Alice')
  })

  // /planning/ui/occurrence-menu/take-over-ask
  // /planning/ui/occurrence-menu/closes
  test('"Yes, take it" closes the menu and the occurrence shows the volunteer', async ({ page, request }) => {
    await openVolunteersSchedule(page, request)
    await dayGroup(page, 1).getByRole('listitem').click()

    await menu(page).getByRole('button', { name: 'Take over this slot…' }).click()
    const dialog = page.getByRole('dialog').filter({ hasText: 'Take this slot from Alice?' })
    await dialog.getByRole('button', { name: 'Yes, take it' }).click()

    await expect(dialog).toBeHidden()
    await expect(menuTitle(page, 1)).toBeHidden()
    await expect(dayGroup(page, 1).getByRole('listitem')).toHaveText('Bruno')
    await page.reload()
    await datastarReady(page)
    await expect(dayGroup(page, 1).getByRole('listitem')).toHaveText('Bruno')
  })
})

test.describe("Schedule menu: the manager's part", () => {
  // /planning/ui/occurrence-menu/propose
  // /planning/operations/register/proposed
  // /planning/ui/schedule/occurrence
  // /planning/ui/occurrence-menu/closes
  test('a name proposes the occurrence to that member and closes the menu', async ({ page, request }) => {
    await openManagersSchedule(page, request)
    await dayGroup(page, 2).getByRole('listitem').click()

    await menu(page).getByRole('button', { name: 'Bruno', exact: true }).click()

    await expect(dayGroup(page, 2).getByRole('listitem')).toHaveText(/^\s*Bruno\s*\?\s*$/)
    await expect(menuTitle(page, 2)).toBeHidden()
    await page.reload()
    await datastarReady(page)
    await expect(dayGroup(page, 2).getByRole('listitem')).toHaveText(/^\s*Bruno\s*\?\s*$/)
  })

  // /ui/errors/generic
  test('proposing when the server fails: the generic error, and the menu stays', async ({ page, request }) => {
    await openManagersSchedule(page, request)
    await page.route('**/propose', (route) => route.fulfill({ status: 500, body: 'failure' }))
    await dayGroup(page, 2).getByRole('listitem').click()

    await menu(page).getByRole('button', { name: 'Bruno', exact: true }).click()

    await expect(page.getByText(GENERIC).filter({ visible: true })).toBeVisible()
    await expect(menuTitle(page, 2)).toBeVisible()
    await expect(dayGroup(page, 2).getByRole('listitem')).toHaveText('')
  })

  // /planning/ui/occurrence-menu/icon
  // /planning/ui/occurrence-menu/note
  // /planning/ui/occurrence-menu/absent
  test('hovering an icon shows its text', async ({ page, request }) => {
    await openManagersSchedule(page, request)
    await dayGroup(page, 2).getByRole('listitem').click()

    await expect(menu(page).getByRole('button', { name: 'Note', exact: true })).toHaveAttribute('title', NOTE)
    await expect(menu(page).getByRole('button', { name: absenceText(), exact: true })).toHaveAttribute(
      'title',
      absenceText(),
    )
  })

  // /planning/ui/occurrence-menu/icon
  // /planning/ui/occurrence-menu/note
  test('clicking an icon shows its text under the names, and proposes nothing', async ({ page, request }) => {
    await openManagersSchedule(page, request)
    await dayGroup(page, 2).getByRole('listitem').click()

    await menu(page).getByRole('button', { name: 'Note', exact: true }).click()

    await expect(page.getByText(NOTE, { exact: true })).toBeVisible()
    await expect(menuTitle(page, 2)).toBeVisible()
    await expect(dayGroup(page, 2).getByRole('listitem')).toHaveText('')
  })

  // /planning/ui/occurrence-menu/icon
  test('clicking the icon again hides its text', async ({ page, request }) => {
    await openManagersSchedule(page, request)
    await dayGroup(page, 2).getByRole('listitem').click()
    const icon = menu(page).getByRole('button', { name: 'Note', exact: true })

    await icon.click()
    await expect(page.getByText(NOTE, { exact: true })).toBeVisible()
    await icon.click()

    await expect(page.getByText(NOTE, { exact: true })).toBeHidden()
    await expect(menuTitle(page, 2)).toBeVisible()
  })

  // /planning/ui/occurrence-menu/icon
  // /planning/ui/occurrence-menu/absent
  test('clicking another icon shows its text in place of the one shown', async ({ page, request }) => {
    await openManagersSchedule(page, request)
    await dayGroup(page, 2).getByRole('listitem').click()

    await menu(page).getByRole('button', { name: 'Note', exact: true }).click()
    await menu(page).getByRole('button', { name: absenceText(), exact: true }).click()

    await expect(page.getByText(absenceText(), { exact: true })).toBeVisible()
    await expect(page.getByText(NOTE, { exact: true })).toBeHidden()
  })

  // /planning/ui/occurrence-menu/icon-reset
  test('the text shown leaves when the menu opens on another occurrence', async ({ page, request }) => {
    await openManagersSchedule(page, request)
    await dayGroup(page, 2).getByRole('listitem').click()
    await menu(page).getByRole('button', { name: 'Note', exact: true }).click()
    await expect(page.getByText(NOTE, { exact: true })).toBeVisible()
    await page.keyboard.press('Escape')

    await dayGroup(page, 3).getByRole('listitem').click()

    await expect(menuTitle(page, 3)).toBeVisible()
    await expect(page.getByText(NOTE, { exact: true })).toBeHidden()
  })
})

test.describe('Schedule menu: the Occurrence menu of a manager', () => {
  // /planning/ui/occurrence-menu/note
  test('the note icon is named "Note" and its description is the note', async ({ page, request }) => {
    await openManagersSchedule(page, request)
    await dayGroup(page, 2).getByRole('listitem').click()

    const icon = menu(page).getByRole('button', { name: 'Note', exact: true })

    await expect(icon).toHaveAccessibleName('Note')
    await expect(icon).toHaveAccessibleDescription(NOTE)
  })

  // /planning/ui/occurrence-menu/taken-names
  test('a taken occurrence offers the names of the other members', async ({ page, request }) => {
    await openManagersSchedule(page, request)
    await dayGroup(page, 1).getByRole('listitem').click()

    await expect(menu(page).getByRole('button', { name: 'Cancel registration…' })).toBeVisible()
    await expect(menu(page).getByRole('button', { name: 'Bruno', exact: true })).toBeVisible()
    await expect(menu(page).getByRole('button', { name: 'Alice', exact: true })).toBeHidden()
  })

  // /planning/ui/occurrence-menu/move
  test('a name on a taken occurrence asks to give the slot; "Keep it" changes nothing', async ({ page, request }) => {
    await openManagersSchedule(page, request)
    await dayGroup(page, 1).getByRole('listitem').click()

    await menu(page).getByRole('button', { name: 'Bruno', exact: true }).click()
    const dialog = page.getByRole('dialog').filter({ hasText: 'Give this slot to Bruno instead of Alice?' })
    await expect(dialog).toBeVisible()
    await dialog.getByRole('button', { name: 'Keep it' }).click()

    await expect(dialog).toBeHidden()
    await expect(dayGroup(page, 1).getByRole('listitem')).toHaveText('Alice')
    await page.reload()
    await datastarReady(page)
    await expect(dayGroup(page, 1).getByRole('listitem')).toHaveText('Alice')
  })

  // /planning/ui/occurrence-menu/move
  // /planning/operations/register/replaced
  // /planning/operations/register/proposed
  test('"Yes, give it" gives the slot to that member, proposed', async ({ page, request }) => {
    await openManagersSchedule(page, request)
    await dayGroup(page, 1).getByRole('listitem').click()

    await menu(page).getByRole('button', { name: 'Bruno', exact: true }).click()
    const dialog = page.getByRole('dialog').filter({ hasText: 'Give this slot to Bruno instead of Alice?' })
    await dialog.getByRole('button', { name: 'Yes, give it' }).click()

    await expect(dayGroup(page, 1).getByRole('listitem')).toHaveText(/^\s*Bruno\s*\?\s*$/)
    await expect(menuTitle(page, 1)).toBeHidden()
    await page.reload()
    await datastarReady(page)
    await expect(dayGroup(page, 1).getByRole('listitem')).toHaveText(/^\s*Bruno\s*\?\s*$/)
  })

  // /planning/ui/occurrence-menu/move-messages
  // /planning/operations/register/taken
  test('"Someone took this slot in the meantime." shows in the confirmation', async ({ page, request }) => {
    await openManagersSchedule(page, request)
    await dayGroup(page, 1).getByRole('listitem').click()
    await menu(page).getByRole('button', { name: 'Bruno', exact: true }).click()
    const dialog = page.getByRole('dialog').filter({ hasText: 'Give this slot to Bruno instead of Alice?' })
    await expect(dialog).toBeVisible()
    const other = await page.context().newPage()
    await other.goto(page.url())
    await datastarReady(other)
    await other.locator('main').getByRole('group', { name: dayOfWeek(4, 1).label, exact: true }).getByRole('listitem').click()
    await other.getByRole('button', { name: 'Cancel registration…' }).click()
    await other.getByRole('button', { name: 'Yes, cancel' }).click()
    await other.locator('main').getByRole('group', { name: dayOfWeek(4, 1).label, exact: true }).getByRole('listitem').click()
    await other.getByRole('button', { name: 'Sign up' }).click()
    await expect(other.locator('main').getByRole('group', { name: dayOfWeek(4, 1).label, exact: true }).getByRole('listitem')).toHaveText('Alice')

    await dialog.getByRole('button', { name: 'Yes, give it' }).click()

    await expect(dialog.getByText(TAKEN).filter({ visible: true })).toBeVisible()
    await expect(dialog.getByText(GENERIC).filter({ visible: true })).toHaveCount(0)
  })

  // /planning/ui/occurrence-menu/fresh
  test('opened again, the menu shows no message of an earlier try', async ({ page, request }) => {
    const slug = await openManagersSchedule(page, request)
    await dayGroup(page, 2).getByRole('listitem').click()
    await expect(menuTitle(page, 2)).toBeVisible()
    await propose(page.request, slug, await userIdOf(page.request, slug, 'Bruno'), dayOfWeek(4, 2).iso, '10:00', '13:00')
    await menu(page).getByRole('button', { name: 'Alice', exact: true }).click()
    await expect(menu(page).getByText(TAKEN).filter({ visible: true })).toBeVisible()
    await page.keyboard.press('Escape')

    await dayGroup(page, 2).getByRole('listitem').click()

    await expect(menuTitle(page, 2)).toBeVisible()
    await expect(page.getByText(TAKEN).filter({ visible: true })).toHaveCount(0)
  })
})

/** Holds the answers of the menu's loads until the test releases them, in the order of the
 * clicks. */
async function holdMenuLoads(page: Page) {
  const held: (() => void)[] = []
  await page.route('**/menu', async (route) => {
    await new Promise<void>((resolve) => held.push(resolve))
    await route.continue()
  })
  return {
    pending: () => held.length,
    release: (n: number) => held[n](),
  }
}

test.describe('Schedule menu: its load', () => {
  // /planning/ui/schedule/opens
  // /planning/ui/schedule/load
  // /planning/ui/schedule/load-shown
  test('the menu opens at once with its title; the rest shows when the load ends', async ({ page, request }) => {
    await openSchedule(page, request)
    const loads = await holdMenuLoads(page)

    await dayGroup(page, 2).getByRole('listitem').click()

    await expect(menuTitle(page, 2)).toBeVisible()
    await expect.poll(() => loads.pending()).toBe(1)
    await expect(page.getByRole('button', { name: 'Sign up' })).toHaveCount(0)
    loads.release(0)
    await expect(page.getByRole('button', { name: 'Sign up' })).toBeVisible()
    await expect(menuTitle(page, 2)).toBeVisible()
  })

  // /planning/ui/schedule/latest
  test('the load of an earlier click changes nothing once a later click opened the menu', async ({ page, request }) => {
    await openSchedule(page, request)
    const loads = await holdMenuLoads(page)
    await dayGroup(page, 2).getByRole('listitem').click()
    await expect.poll(() => loads.pending()).toBe(1)
    await page.keyboard.press('Escape')
    await expect(menuTitle(page, 2)).toBeHidden()
    await dayGroup(page, 3).getByRole('listitem').click()
    await expect.poll(() => loads.pending()).toBe(2)

    loads.release(1)
    await expect(page.getByRole('button', { name: 'Sign up' })).toBeVisible()
    loads.release(0)
    await page.waitForTimeout(500)

    await expect(menuTitle(page, 3)).toBeVisible()
    await expect(menuTitle(page, 2)).toBeHidden()
    await expect(page.getByRole('button', { name: 'Sign up' })).toHaveCount(1)
  })

  // /planning/ui/schedule/latest
  test('the load of a click ending after the menu closed shows nothing', async ({ page, request }) => {
    await openSchedule(page, request)
    const loads = await holdMenuLoads(page)
    await dayGroup(page, 2).getByRole('listitem').click()
    await expect.poll(() => loads.pending()).toBe(1)
    await page.keyboard.press('Escape')
    await expect(menuTitle(page, 2)).toBeHidden()

    loads.release(0)
    await page.waitForTimeout(500)

    await expect(menuTitle(page, 2)).toBeHidden()
    await expect(page.getByRole('button', { name: 'Sign up' })).toBeHidden()
  })

  // /planning/ui/schedule/load-failed
  test('a load that fails shows only its title and the generic error', async ({ page, request }) => {
    await openSchedule(page, request)
    await page.route('**/menu', (route) => route.fulfill({ status: 500, body: 'failure' }))

    await dayGroup(page, 2).getByRole('listitem').click()

    await expect(menuTitle(page, 2)).toBeVisible()
    await expect(menu(page).getByText(GENERIC).filter({ visible: true })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Sign up' })).toBeHidden()
  })

  // /planning/ui/schedule/load-signed-out
  test('signed out meanwhile, it leads to Sign in', async ({ page, request }) => {
    await openSchedule(page, request)
    const other = await page.context().newPage()
    await other.goto('/')
    await datastarReady(other)
    await other.locator('header').getByRole('button', { name: 'Alice' }).click()
    await other.getByRole('button', { name: 'Sign out' }).click()
    await expect(other.getByRole('button', { name: 'Sign in' })).toBeVisible()
    await other.close()

    await dayGroup(page, 2).getByRole('listitem').click()

    await expect(page.getByRole('button', { name: 'Sign in' })).toBeVisible()
  })
})

test.describe('Schedule menu: taken', () => {
  // /planning/ui/schedule/taken
  // /planning/ui/occurrence-menu/taken
  test('after "Someone took this slot in the meantime." the Schedule shows who took it, the menu staying open', async ({
    page,
    request,
  }) => {
    const slug = await openManagersSchedule(page, request)
    await dayGroup(page, 2).getByRole('listitem').click()
    await expect(menuTitle(page, 2)).toBeVisible()
    await propose(page.request, slug, await userIdOf(page.request, slug, 'Bruno'), dayOfWeek(4, 2).iso, '10:00', '13:00')
    await expect(dayGroup(page, 2).getByRole('listitem')).toHaveText('')

    await menu(page).getByRole('button', { name: 'Alice', exact: true }).click()

    await expect(menu(page).getByText(TAKEN).filter({ visible: true })).toBeVisible()
    await expect(dayGroup(page, 2).getByRole('listitem')).toHaveText(/^\s*Bruno\s*\?\s*$/)
    await expect(menuTitle(page, 2)).toBeVisible()
  })
})

/** Moves the browser's clock two days on and lets a minute pass, as a page left open past
 * midnight. The page must have been loaded after `page.clock.install()`. */
async function nextDay(page: Page) {
  await page.clock.fastForward('48:00:00')
  await page.clock.runFor(60_000)
}

/** Simulates a screen hidden, then shown again. */
async function setHidden(page: Page, hidden: boolean) {
  await page.evaluate((value) => {
    Object.defineProperty(document, 'hidden', { configurable: true, get: () => value })
    Object.defineProperty(document, 'visibilityState', {
      configurable: true,
      get: () => (value ? 'hidden' : 'visible'),
    })
    document.dispatchEvent(new Event('visibilitychange'))
  }, hidden)
}

/** The Schedule of `openManagersSchedule`, opened with a clock that the test moves. */
async function openScheduleWithClock(page: Page, request: APIRequestContext) {
  await page.clock.install()
  return await openManagersSchedule(page, request)
}

test.describe('Schedule: once today changes', () => {
  // /planning/ui/schedule/new-day
  test('it shows what changed elsewhere without a reload, an open menu staying open', async ({ page, request }) => {
    const slug = await openScheduleWithClock(page, request)
    await page.evaluate(() => ((window as unknown as { sameDocument: boolean }).sameDocument = true))
    await dayGroup(page, 2).getByRole('listitem').click()
    await expect(menuTitle(page, 2)).toBeVisible()
    await signUpFor(page.request, slug, dayOfWeek(4, 3).iso, '10:00', '13:00')
    await expect(dayGroup(page, 3).getByRole('listitem')).toHaveText('')

    await nextDay(page)

    await expect(dayGroup(page, 3).getByRole('listitem')).toHaveText('Alice')
    await expect(menuTitle(page, 2)).toBeVisible()
    await expect(page.getByRole('button', { name: 'Sign up' })).toBeVisible()
    expect(await page.evaluate(() => (window as unknown as { sameDocument?: boolean }).sameDocument)).toBe(true)
  })

  // /planning/ui/schedule/new-day
  test('it keeps the weeks shown, More weeks included', async ({ page, request }) => {
    const slug = await openScheduleWithClock(page, request)
    await page.getByRole('button', { name: 'More weeks' }).click()
    await expect(weekHeadings(page)).toHaveCount(10)
    await signUpFor(page.request, slug, dayOfWeek(4, 8).iso, '10:00', '13:00')

    await nextDay(page)

    await expect(dayGroup(page, 8).getByRole('listitem')).toHaveText('Alice')
    await expect(weekHeadings(page)).toHaveCount(10)
  })

  // /planning/ui/schedule/new-day
  test('a screen hidden then shown again after the change shows it within a minute', async ({ page, request }) => {
    const slug = await openScheduleWithClock(page, request)
    await setHidden(page, true)
    await signUpFor(page.request, slug, dayOfWeek(4, 3).iso, '10:00', '13:00')
    await nextDay(page)

    await setHidden(page, false)
    await page.clock.runFor(60_000)

    await expect(dayGroup(page, 3).getByRole('listitem')).toHaveText('Alice')
  })

  // /planning/ui/schedule/new-day-signed-out
  test('signed out meanwhile, it leads to Sign in', async ({ page, request }) => {
    await openScheduleWithClock(page, request)
    const other = await page.context().newPage()
    await other.goto('/')
    await datastarReady(other)
    await other.locator('header').getByRole('button', { name: 'Alice' }).click()
    await other.getByRole('button', { name: 'Sign out' }).click()
    await expect(other.getByRole('button', { name: 'Sign in' })).toBeVisible()
    await other.close()

    await nextDay(page)

    await expect(page.getByRole('button', { name: 'Sign in' })).toBeVisible()
  })

  // /planning/ui/schedule/new-day-failed
  test('when it fails, the Schedule stays as it was, with no message', async ({ page, request }) => {
    const slug = await openScheduleWithClock(page, request)
    let refreshes = 0
    await page.route(/\/weeks-again\?/, (route) => {
      if (route.request().method() !== 'GET') return route.continue()
      refreshes += 1
      return route.fulfill({ status: 500, body: 'failure' })
    })
    await signUpFor(page.request, slug, dayOfWeek(4, 3).iso, '10:00', '13:00')

    await nextDay(page)
    await page.waitForTimeout(500)

    expect(refreshes).toBeGreaterThan(0)
    await expect(dayGroup(page, 3).getByRole('listitem')).toHaveText('')
    await expect(weekHeadings(page)).toHaveCount(6)
    await expect(page.locator('main').getByText(GENERIC).filter({ visible: true })).toHaveCount(0)
  })
})
