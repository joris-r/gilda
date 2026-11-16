import { expect, test, type APIRequestContext, type Browser, type Page } from '@playwright/test'
import { addSlot, createAssociation, signUpFor, signedIn, datastarReady } from './helpers'

const GENERIC = 'Something went wrong. Try again.'
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
 * up for next week's Thursday, creates its share link on Schedule settings, and returns it. */
async function shareSchedule(page: Page, request: APIRequestContext) {
  await signedIn(page, request)
  const slug = await createAssociation(page.request)
  await addSlot(page.request, slug, 'thursday', '10:00', '13:00')
  await signUpFor(page.request, slug, dayOfWeek(4, 1).iso, '10:00', '13:00')
  await page.goto(`/association/${slug}/settings`)
  await datastarReady(page)
  await page.getByRole('button', { name: 'Create a share link' }).click()
  const shown = page.locator('main').getByText(/\/shared\/[\w-]+/)
  await expect(shown).toBeVisible()
  const match = /https?:\/\/\S+\/shared\/[\w-]+/.exec((await shown.textContent()) ?? '')
  expect(match).not.toBeNull()
  return match![0]
}

/** Opens `link` in a new browser context, signed out. */
async function openSignedOut(link: string, browser: Browser) {
  const context = await browser.newContext()
  const visitor = await context.newPage()
  const response = await visitor.goto(link)
  await datastarReady(visitor)
  expect(response?.status()).toBe(200)
  return visitor
}

function weekHeadings(page: Page) {
  return page.locator('main').getByRole('heading', { name: /^(Week|Semaine) \d+$/ })
}

function dayGroup(page: Page, weeksAhead: number) {
  return page.getByRole('group', { name: dayOfWeek(4, weeksAhead).label, exact: true })
}

test.describe('Shared schedule', () => {

  // /planning/ui/shared-schedule/shown
  test('clicking an occurrence opens no menu', async ({ page, request, browser }) => {
    const link = await shareSchedule(page, request)
    const visitor = await openSignedOut(link, browser)
    const requests: string[] = []
    visitor.on('request', (sent) => requests.push(sent.url()))

    await dayGroup(visitor, 2).getByRole('listitem').click()
    await dayGroup(visitor, 1).getByRole('listitem').click()

    await expect(visitor.getByRole('button', { name: 'Sign up' })).toHaveCount(0)
    await expect(visitor.getByText(`${dayOfWeek(4, 2).label} · 10–13`, { exact: true })).toBeHidden()
    expect(requests.filter((url) => url.includes('/menu'))).toEqual([])
  })

  // /planning/ui/schedule/more
  test('"More weeks", at the end, adds four more each time', async ({ page, request, browser }) => {
    const link = await shareSchedule(page, request)
    const visitor = await openSignedOut(link, browser)

    await visitor.getByRole('button', { name: 'More weeks' }).click()
    await expect(weekHeadings(visitor)).toHaveCount(10)
    await visitor.getByRole('button', { name: 'More weeks' }).click()

    await expect(weekHeadings(visitor)).toHaveCount(14)
    await expect(dayGroup(visitor, 12)).toBeVisible()
    await expect(dayGroup(visitor, 1).getByRole('listitem')).toHaveText('Alice')
  })

  // /ui/errors/generic
  test('"More weeks" when the server fails: the generic error', async ({ page, request, browser }) => {
    const link = await shareSchedule(page, request)
    const visitor = await openSignedOut(link, browser)
    await visitor.route('**/weeks', (route) => route.fulfill({ status: 500, body: 'failure' }))

    await visitor.getByRole('button', { name: 'More weeks' }).click()

    await expect(visitor.locator('main').getByText(GENERIC).filter({ visible: true })).toBeVisible()
    await expect(weekHeadings(visitor)).toHaveCount(6)
  })

  // /core/ui/header/shared
  // /core/ui/header/language
  test('the language selector switches it to French', async ({ page, request, browser }) => {
    const link = await shareSchedule(page, request)
    const visitor = await openSignedOut(link, browser)

    await visitor.locator('header').getByRole('combobox').selectOption({ label: 'Français' })

    await expect(visitor.locator('main').getByRole('heading', { name: /^Semaine \d+$/ }).first()).toBeVisible()
    await expect(visitor.getByRole('button', { name: 'Plus de semaines' })).toBeVisible()
  })
})

/** Opens `link` in a new browser context, signed out, with a clock that the test moves. */
async function openSignedOutWithClock(link: string, browser: Browser) {
  const context = await browser.newContext()
  const visitor = await context.newPage()
  await visitor.clock.install()
  const response = await visitor.goto(link)
  await datastarReady(visitor)
  expect(response?.status()).toBe(200)
  await expect(weekHeadings(visitor).first()).toBeVisible()
  return visitor
}

/** Moves the browser's clock two days on and lets a minute pass, as a page left open past
 * midnight. */
async function nextDay(page: Page) {
  await page.clock.fastForward('48:00:00')
  await page.clock.runFor(60_000)
}

/** Alice revokes the share link, from the Schedule settings she has open on `page`. */
async function revokeLink(page: Page) {
  const slug = /\/association\/([^/]+)\/settings/.exec(page.url())![1]
  const response = await page.request.post(`/association/${slug}/settings/share-link/revoke`, { data: {} })
  expect(response.status()).toBe(200)
  return slug
}

const INVALID = 'This link is no longer valid.'

test.describe('Shared schedule: once today changes', () => {
  // /planning/ui/shared-schedule/new-day
  // /planning/ui/schedule/new-day
  test('it shows what changed elsewhere without a reload, with the weeks shown', async ({ page, request, browser }) => {
    const link = await shareSchedule(page, request)
    const slug = /\/association\/([^/]+)\/settings/.exec(page.url())![1]
    const visitor = await openSignedOutWithClock(link, browser)
    await visitor.getByRole('button', { name: 'More weeks' }).click()
    await expect(weekHeadings(visitor)).toHaveCount(10)
    await visitor.evaluate(() => ((window as unknown as { sameDocument: boolean }).sameDocument = true))
    await signUpFor(page.request, slug, dayOfWeek(4, 3).iso, '10:00', '13:00')
    await expect(dayGroup(visitor, 3).getByRole('listitem')).toHaveText('')

    await nextDay(visitor)

    await expect(dayGroup(visitor, 3).getByRole('listitem')).toHaveText('Alice')
    await expect(weekHeadings(visitor)).toHaveCount(10)
    await expect(visitor.getByRole('button', { name: 'Sign up' })).toHaveCount(0)
    expect(await visitor.evaluate(() => (window as unknown as { sameDocument?: boolean }).sameDocument)).toBe(true)
  })

  // /planning/ui/shared-schedule/new-day
  test('when it fails, it stays as it was, with no message', async ({ page, request, browser }) => {
    const link = await shareSchedule(page, request)
    const slug = /\/association\/([^/]+)\/settings/.exec(page.url())![1]
    const visitor = await openSignedOutWithClock(link, browser)
    let refreshes = 0
    await visitor.route(/\/weeks-again\?/, (route) => {
      if (route.request().method() !== 'GET') return route.continue()
      refreshes += 1
      return route.fulfill({ status: 500, body: 'failure' })
    })
    await signUpFor(page.request, slug, dayOfWeek(4, 3).iso, '10:00', '13:00')

    await nextDay(visitor)
    await visitor.waitForTimeout(500)

    expect(refreshes).toBeGreaterThan(0)
    await expect(dayGroup(visitor, 3).getByRole('listitem')).toHaveText('')
    await expect(weekHeadings(visitor)).toHaveCount(6)
    await expect(visitor.locator('main').getByText(GENERIC).filter({ visible: true })).toHaveCount(0)
    await expect(visitor.locator('main').getByText(INVALID)).toHaveCount(0)
  })

  // /planning/ui/shared-schedule/gone
  // /planning/ui/shared-schedule/new-day
  test('a link revoked meanwhile shows as no longer valid', async ({ page, request, browser }) => {
    const link = await shareSchedule(page, request)
    const visitor = await openSignedOutWithClock(link, browser)
    await revokeLink(page)

    await nextDay(visitor)

    await expect(visitor.locator('main').getByText(INVALID)).toBeVisible()
    await expect(weekHeadings(visitor)).toHaveCount(0)
    await expect(visitor.locator('main').getByText(GENERIC).filter({ visible: true })).toHaveCount(0)
  })
})

test.describe('Shared schedule: a link that is gone', () => {
  // /planning/ui/shared-schedule/gone
  test('"More weeks" shows "This link is no longer valid." and no generic error', async ({ page, request, browser }) => {
    const link = await shareSchedule(page, request)
    const visitor = await openSignedOut(link, browser)
    await revokeLink(page)

    await visitor.getByRole('button', { name: 'More weeks' }).click()

    await expect(visitor.locator('main').getByText(INVALID)).toBeVisible()
    await expect(visitor.locator('main').getByText(GENERIC).filter({ visible: true })).toHaveCount(0)
    await expect(weekHeadings(visitor)).toHaveCount(0)
  })
})
