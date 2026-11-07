import { expect, test, type APIRequestContext, type Browser, type Page } from '@playwright/test'
import { addSlot, createAssociation, signUpFor, signedIn } from './helpers'

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
  test('signed out, it shows the Schedule with the registrations', async ({ page, request, browser }) => {
    const link = await shareSchedule(page, request)

    const visitor = await openSignedOut(link, browser)

    await expect(weekHeadings(visitor)).toHaveCount(6)
    await expect(dayGroup(visitor, 1).getByRole('listitem')).toHaveText('Alice')
  })

  test('signed in, it shows the same', async ({ page, request }) => {
    const link = await shareSchedule(page, request)

    const response = await page.goto(link)

    expect(response?.status()).toBe(200)
    await expect(weekHeadings(page)).toHaveCount(6)
    await expect(dayGroup(page, 1).getByRole('listitem')).toHaveText('Alice')
  })

  test('the header shows the association name leading nowhere, and the language selector alone', async ({
    page,
    request,
    browser,
  }) => {
    const link = await shareSchedule(page, request)

    const visitor = await openSignedOut(link, browser)

    const header = visitor.locator('header')
    await expect(header.getByText('Jardin partagé', { exact: true })).toBeVisible()
    await expect(header.getByRole('link', { name: 'Jardin partagé' })).toHaveCount(0)
    await expect(header.getByRole('combobox')).toBeVisible()
  })

  test('signed in, the header has no menu of the user', async ({ page, request }) => {
    const link = await shareSchedule(page, request)

    await page.goto(link)

    const header = page.locator('header')
    await expect(header.getByText('Jardin partagé', { exact: true })).toBeVisible()
    await expect(header.getByText('Alice')).toHaveCount(0)
    await expect(page.getByText('Sign out', { exact: true })).toHaveCount(0)
  })

  test('it has no links to the other screens', async ({ page, request, browser }) => {
    const link = await shareSchedule(page, request)

    const visitor = await openSignedOut(link, browser)

    await expect(weekHeadings(visitor).first()).toBeVisible()
    for (const screen of ['My availability', 'Members', 'Schedule settings']) {
      await expect(visitor.getByRole('link', { name: screen, exact: true })).toHaveCount(0)
    }
  })

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

  test('"More weeks" when the server fails: the generic error', async ({ page, request, browser }) => {
    const link = await shareSchedule(page, request)
    const visitor = await openSignedOut(link, browser)
    await visitor.route('**/weeks', (route) => route.fulfill({ status: 500, body: 'failure' }))

    await visitor.getByRole('button', { name: 'More weeks' }).click()

    await expect(visitor.locator('main').getByText(GENERIC).filter({ visible: true })).toBeVisible()
    await expect(weekHeadings(visitor)).toHaveCount(6)
  })

  test('the language selector switches it to French', async ({ page, request, browser }) => {
    const link = await shareSchedule(page, request)
    const visitor = await openSignedOut(link, browser)

    await visitor.locator('header').getByRole('combobox').selectOption({ label: 'Français' })

    await expect(visitor.locator('main').getByRole('heading', { name: /^Semaine \d+$/ }).first()).toBeVisible()
    await expect(visitor.getByRole('button', { name: 'Plus de semaines' })).toBeVisible()
  })

  test('an unknown link says "This link is no longer valid."', async ({ browser, baseURL }) => {
    const visitor = await openSignedOut(`${baseURL}/shared/unknown-token`, browser)

    await expect(visitor.locator('main').getByText('This link is no longer valid.')).toBeVisible()
    await expect(visitor.getByText('Page not found')).toHaveCount(0)
  })
})
