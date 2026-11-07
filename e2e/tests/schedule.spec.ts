import { expect, test, type APIRequestContext, type Page } from '@playwright/test'
import { PASSWORD, latestToken, uniqueEmail } from './helpers'

const GENERIC = 'Something went wrong. Try again.'
const WEEKDAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

function uniqueSlug() {
  return `e2e-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

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
  const slot = await page.request.post(`/api/associations/${id}/slots`, {
    data: { weekday: 'thursday', start: '10:00', end: '13:00' },
  })
  expect(slot.status()).toBe(201)
  const session = await page.request.get('/api/session')
  const { id: userId } = (await session.json()) as { id: string }
  const registration = await page.request.post(`/api/associations/${id}/registrations`, {
    data: { user_id: userId, date: dayOfWeek(4, 1).iso, start: '10:00', end: '13:00' },
  })
  expect(registration.status()).toBe(201)
  await page.goto(`/association/${slug}`)
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
    test(`"${screen}" leads to that screen`, async ({ page, request }) => {
      const slug = await openSchedule(page, request)

      await page.getByRole('link', { name: screen, exact: true }).click()

      await expect(page).toHaveURL(new RegExp(`/association/${slug}/${rest}$`))
      await expect(page.locator('header').getByText(screen)).toBeVisible()
    })
  }

  test('each day is a group named by its day, holding its occurrences', async ({ page, request }) => {
    await openSchedule(page, request)

    const day = page.getByRole('group', { name: dayOfWeek(4, 1).label, exact: true })

    await expect(day.getByRole('listitem')).toHaveCount(1)
    await expect(day.getByRole('listitem')).toHaveText('Alice')
  })

  test('opens on six weeks', async ({ page, request }) => {
    await openSchedule(page, request)

    await expect(weekHeadings(page)).toHaveCount(6)
  })

  test('"More weeks", at the end, adds four more', async ({ page, request }) => {
    await openSchedule(page, request)
    const last = await weekHeadings(page).last().textContent()

    await page.getByRole('button', { name: 'More weeks' }).click()

    await expect(weekHeadings(page)).toHaveCount(10)
    await expect(weekHeadings(page).nth(6)).not.toHaveText(last ?? '')
    await expect(page.getByRole('group', { name: dayOfWeek(4, 8).label, exact: true })).toBeVisible()
  })

  test('"More weeks" adds four more each time', async ({ page, request }) => {
    await openSchedule(page, request)

    await page.getByRole('button', { name: 'More weeks' }).click()
    await expect(weekHeadings(page)).toHaveCount(10)
    await page.getByRole('button', { name: 'More weeks' }).click()

    await expect(weekHeadings(page)).toHaveCount(14)
    await expect(page.getByRole('group', { name: dayOfWeek(4, 12).label, exact: true })).toBeVisible()
  })

  test('the weeks added keep the occurrences shown', async ({ page, request }) => {
    await openSchedule(page, request)

    await page.getByRole('button', { name: 'More weeks' }).click()

    await expect(weekHeadings(page)).toHaveCount(10)
    const day = page.getByRole('group', { name: dayOfWeek(4, 1).label, exact: true })
    await expect(day.getByRole('listitem')).toHaveText('Alice')
  })

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
  test('clicking an occurrence from today on opens its menu, titled with its day and times', async ({ page, request }) => {
    await openSchedule(page, request)

    await dayGroup(page, 2).getByRole('listitem').click()

    await expect(menuTitle(page, 2)).toBeVisible()
    await expect(page.getByRole('button', { name: 'Sign up' })).toBeVisible()
  })

  test('clicking an occurrence before today opens nothing', async ({ page, request }) => {
    await openSchedule(page, request)

    await dayGroup(page, -1).getByRole('listitem').click()

    await expect(menuTitle(page, -1)).toBeHidden()
    await expect(page.getByRole('button', { name: 'Sign up' })).toBeHidden()
  })

  test('Escape closes the menu', async ({ page, request }) => {
    await openSchedule(page, request)
    await dayGroup(page, 2).getByRole('listitem').click()
    await expect(menuTitle(page, 2)).toBeVisible()

    await page.keyboard.press('Escape')

    await expect(menuTitle(page, 2)).toBeHidden()
  })

  test('"Sign up" closes the menu and the occurrence shows the user', async ({ page, request }) => {
    await openSchedule(page, request)
    await dayGroup(page, 2).getByRole('listitem').click()

    await page.getByRole('button', { name: 'Sign up' }).click()

    await expect(dayGroup(page, 2).getByRole('listitem')).toHaveText('Alice')
    await expect(menuTitle(page, 2)).toBeHidden()
    await page.reload()
    await expect(dayGroup(page, 2).getByRole('listitem')).toHaveText('Alice')
  })

  test('"Sign up" keeps the weeks shown', async ({ page, request }) => {
    await openSchedule(page, request)
    await page.getByRole('button', { name: 'More weeks' }).click()
    await expect(weekHeadings(page)).toHaveCount(10)
    await dayGroup(page, 8).getByRole('listitem').click()

    await page.getByRole('button', { name: 'Sign up' }).click()

    await expect(dayGroup(page, 8).getByRole('listitem')).toHaveText('Alice')
    await expect(weekHeadings(page)).toHaveCount(10)
  })

  test('"Sign up" when the server fails: the generic error, and the menu stays', async ({ page, request }) => {
    await openSchedule(page, request)
    await page.route('**/sign-up', (route) => route.fulfill({ status: 500, body: 'failure' }))
    await dayGroup(page, 2).getByRole('listitem').click()

    await page.getByRole('button', { name: 'Sign up' }).click()

    await expect(page.getByText(GENERIC).filter({ visible: true })).toBeVisible()
    await expect(menuTitle(page, 2)).toBeVisible()
    await expect(dayGroup(page, 2).getByRole('listitem')).toHaveText('')
  })

  test('"Cancel registration…" asks first; "Keep it" changes nothing', async ({ page, request }) => {
    await openSchedule(page, request)
    await dayGroup(page, 1).getByRole('listitem').click()

    await page.getByRole('button', { name: 'Cancel registration…' }).click()
    const dialog = page.getByRole('dialog').filter({ hasText: 'Cancel this registration?' })
    await expect(dialog).toBeVisible()
    await dialog.getByRole('button', { name: 'Keep it' }).click()

    await expect(dialog).toBeHidden()
    await page.reload()
    await dayGroup(page, 1).getByRole('listitem').click()
    await expect(page.getByRole('button', { name: 'Cancel registration…' })).toBeVisible()
  })

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
