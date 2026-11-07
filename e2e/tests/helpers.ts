import { expect, type APIRequestContext, type Page } from '@playwright/test'

export const PASSWORD = 'correct horse'
const MAILPIT_URL = process.env.MAILPIT_URL ?? 'http://localhost:18025'

export function uniqueEmail(name: string) {
  return `${name.toLowerCase()}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}@example.org`
}

/** Reads the latest link Mailpit caught for `email`, and returns its token. */
export async function latestToken(email: string, timeout = 5000): Promise<string> {
  const deadline = Date.now() + timeout
  while (true) {
    const search = await fetch(
      `${MAILPIT_URL}/api/v1/search?query=${encodeURIComponent(`to:${email}`)}`,
    )
    const { messages } = (await search.json()) as { messages: { ID: string; Created: string }[] }
    if (messages.length > 0) {
      // Mailpit IDs are not ordered by time; Created has millisecond precision.
      const latest = messages.reduce((a, b) => (Date.parse(a.Created) > Date.parse(b.Created) ? a : b))
      const message = await fetch(`${MAILPIT_URL}/api/v1/message/${latest.ID}`)
      const { Text: text } = (await message.json()) as { Text: string }
      const match = /token=([\w-]+)/.exec(text)
      if (!match) throw new Error(`no link with a token in the email sent to ${email}`)
      return match[1]
    }
    if (Date.now() > deadline) throw new Error(`no email was sent to ${email}`)
    await new Promise((resolve) => setTimeout(resolve, 200))
  }
}

const GENERIC = 'Something went wrong. Try again.'

export function uniqueSlug() {
  return `e2e-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

/** Creates the account of `displayName` with Create an account, confirms its email, and returns
 * the email; `request` is then signed in as that user. */
export async function createAccount(
  request: APIRequestContext,
  displayName = 'Alice',
  email = uniqueEmail(displayName),
) {
  expect((await request.post('/signup', { data: { displayName, email, password: PASSWORD } })).status()).toBe(200)
  const token = await latestToken(email)
  expect((await request.post('/verify-email', { data: { token } })).status()).toBe(200)
  return email
}

/** Signs in on `page` with Sign in, and waits for My associations. */
export async function signIn(page: Page, email: string, password = PASSWORD) {
  await page.goto('/')
  await page.getByLabel('Email', { exact: true }).fill(email)
  await page.getByLabel('Password', { exact: true }).fill(password)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page.locator('header').getByText('My associations')).toBeVisible()
}

/** Creates Alice's account and signs her in on `page`; returns her email. */
export async function signedIn(page: Page, request: APIRequestContext) {
  const email = await createAccount(request)
  await signIn(page, email)
  return email
}

/** Runs a screen's action with `signals`, as its page does, and returns its response. */
async function run(api: APIRequestContext, path: string, signals: object) {
  const response = await api.post(path, { data: signals })
  expect(response.status()).toBe(200)
  return response.text()
}

/** Runs a screen's action with `signals`, and checks that it shows no generic error. */
async function act(api: APIRequestContext, path: string, signals: object) {
  const text = await run(api, path, signals)
  expect(text).not.toContain(GENERIC)
  return text
}

/** Creates an association on New association; returns its slug. */
export async function createAssociation(api: APIRequestContext, name = 'Jardin partagé', slug = uniqueSlug()) {
  expect(await act(api, '/association/new', { name, slug })).toContain(`/association/${slug}`)
  return slug
}

/** Adds a member with "Add a member" on Members. */
export async function addMember(
  api: APIRequestContext,
  slug: string,
  displayName: string,
  email = uniqueEmail('Member'),
  role = 'volunteer',
) {
  // Members sends back its list, whose dialogs hold hidden copies of the generic error.
  expect(await run(api, `/association/${slug}/members`, { displayName, email, role })).toContain(' added.')
}

/** The user id of the member `displayName`, as the edit icon of their line on Members holds it. */
export async function userIdOf(api: APIRequestContext, slug: string, displayName: string) {
  const page = await (await api.get(`/association/${slug}/members`)).text()
  const match = new RegExp(`aria-label="Edit ${displayName}"[^>]*commandfor="edit-([\\w-]+)"`).exec(page)
  if (!match) throw new Error(`no member ${displayName} on Members`)
  return match[1]
}

/** Adds a slot with "Add a slot" on Schedule settings. */
export async function addSlot(api: APIRequestContext, slug: string, weekday: string, start: string, end: string) {
  await act(api, `/association/${slug}/settings/slots`, { weekday, start, end })
}

/** Adds a closure with "Add a closure" on Schedule settings. */
export async function addClosure(api: APIRequestContext, slug: string, first: string, last: string, label = '') {
  await act(api, `/association/${slug}/settings/closures`, { first, last, label })
}

/** Saves the dialog "Planning period" on Schedule settings. */
export async function setPeriod(api: APIRequestContext, slug: string, first: string, last: string) {
  await act(api, `/association/${slug}/settings/period`, { first, last })
}

/** Adds an absence of the user's own with "Add an absence" on My availability. */
export async function addAbsence(api: APIRequestContext, slug: string, first: string, last: string) {
  await act(api, `/association/${slug}/availability/absences`, { first, last })
}

/** Saves the user's own "Note for the managers" on My availability. */
export async function saveNote(api: APIRequestContext, slug: string, text: string) {
  await act(api, `/association/${slug}/availability/note`, { text })
}

/** Clicks "Sign up" in the menu of the occurrence of `date` on the Schedule. */
export async function signUpFor(api: APIRequestContext, slug: string, date: string, start: string, end: string) {
  await act(api, `/association/${slug}/sign-up`, { date, start, end, from: date, to: date })
}

/** Clicks the display name of the member `userId` in the menu of the occurrence of `date` on the
 * Schedule. */
export async function propose(
  api: APIRequestContext,
  slug: string,
  userId: string,
  date: string,
  start: string,
  end: string,
) {
  await act(api, `/association/${slug}/propose`, { user_id: userId, date, start, end, from: date, to: date })
}
