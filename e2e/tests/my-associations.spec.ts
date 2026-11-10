import { expect, test, type APIRequestContext, type Page } from '@playwright/test'
import {
  addClosure,
  addMember,
  addSlot,
  createAccount,
  createAssociation,
  propose,
  setPeriod,
  signUpFor,
  signedIn,
  uniqueEmail,
  uniqueSlug,
  userIdOf,
} from './helpers'

const GENERIC = 'Something went wrong. Try again.'
const MALFORMED =
  'Use only lowercase letters, digits and hyphens, starting and ending with a letter or a digit.'
const TAKEN = 'This association identifier is already taken.'

function nameField(page: Page) {
  return page.getByLabel('Name', { exact: true })
}

function identifierField(page: Page) {
  return page.getByLabel('Association identifier')
}

function createButton(page: Page) {
  return page.getByRole('button', { name: 'Create association' })
}

const WEEKDAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

/** Next week's Thursday, as the actions take it and as My associations shows it. */
function nextThursday() {
  const day = new Date()
  day.setHours(12, 0, 0, 0)
  day.setDate(day.getDate() - ((day.getDay() + 6) % 7) + 7 + 3)
  const iso = `${day.getFullYear()}-${String(day.getMonth() + 1).padStart(2, '0')}-${String(day.getDate()).padStart(2, '0')}`
  return { iso, label: `${WEEKDAYS[day.getDay()]} ${day.getDate()} ${MONTHS[day.getMonth()]}` }
}

/** Alice, signed in on `page`, manages Jardin partagé, open on Thursdays from 10:00 to 13:00. */
async function withAssociation(page: Page, request: APIRequestContext) {
  await signedIn(page, request)
  const slug = await createAssociation(page.request)
  await addSlot(page.request, slug, 'thursday', '10:00', '13:00')
  return slug
}

/** Bruno, a manager of the association signed in on `request`, proposes next week's Thursday to
 * Alice. */
async function proposedToAlice(page: Page, request: APIRequestContext) {
  const slug = await withAssociation(page, request)
  const alice = await userIdOf(page.request, slug, 'Alice')
  const bruno = uniqueEmail('Bruno')
  await addMember(page.request, slug, 'Bruno', bruno, 'manager')
  await createAccount(request, 'Bruno', bruno)
  await propose(request, slug, alice, nextThursday().iso, '10:00', '13:00')
  await page.goto('/')
}

function jardin(page: Page) {
  return page.locator('main').getByRole('listitem').filter({ hasText: 'Jardin partagé' })
}

test.describe('My associations', () => {
  // /home/ui/my-associations/new
  // /core/ui/new-association/cancel
  // /home/ui/my-associations/none
  test('New association leads to its screen, and Cancel back', async ({ page, request }) => {
    await signedIn(page, request)

    await page.getByRole('link', { name: 'New association' }).click()
    await expect(page).toHaveURL(/\/association\/new$/)
    await expect(page.getByRole('heading', { name: 'New association' })).toBeVisible()

    await page.getByRole('link', { name: 'Cancel' }).click()
    await expect(page).toHaveURL(/\/$/)
    await expect(page.getByText('You are not a member of any association yet.')).toBeVisible()
  })

  // /core/ui/header/location
  test("the header's My associations leads back from New association", async ({
    page,
    request,
  }) => {
    await signedIn(page, request)
    await page.goto('/association/new')

    await page.locator('header').getByRole('link', { name: 'My associations' }).click()

    await expect(page).toHaveURL(/\/$/)
  })

  // /home/ui/my-associations/list
  test("a name leads to the association's Schedule", async ({ page, request }) => {
    await signedIn(page, request)
    const slug = uniqueSlug()
    await page.goto('/association/new')
    await nameField(page).fill('Jardin partagé')
    await identifierField(page).fill(slug)
    await createButton(page).click()
    await expect(page).toHaveURL(new RegExp(`/association/${slug}$`))
    await page.goto('/')

    await page.getByRole('link', { name: 'Jardin partagé' }).click()

    await expect(page).toHaveURL(new RegExp(`/association/${slug}$`))
  })
})

test.describe('Registrations summary', () => {
  // /home/ui/my-associations/confirm
  // /home/ui/my-associations/upcoming
  // /home/ui/my-associations/registration
  // /planning/operations/change-registration/confirm
  test('Confirm confirms the registration, and the summary shows it at once', async ({
    page,
    request,
  }) => {
    await proposedToAlice(page, request)
    const line = `${nextThursday().label}, 10:00–13:00 Alice`
    await expect(jardin(page)).toContainText(`${line} ?`)

    await jardin(page).getByRole('button', { name: 'Confirm', exact: true }).click()

    await expect(jardin(page)).not.toContainText('?')
    await expect(jardin(page)).toContainText(line)
    await expect(jardin(page).getByRole('button', { name: 'Confirm', exact: true })).toHaveCount(0)
  })

  // /home/ui/my-associations/acknowledge
  // /home/ui/my-associations/obsolete
  // /home/operations/list-my-associations/obsolete
  test('OK cancels the obsolete registration, which no longer shows', async ({ page, request }) => {
    const slug = await withAssociation(page, request)
    const thursday = nextThursday().iso
    await signUpFor(page.request, slug, thursday, '10:00', '13:00')
    await addClosure(page.request, slug, thursday, thursday)
    await page.goto('/')
    await expect(jardin(page)).toContainText('this slot no longer takes place.')

    await jardin(page).getByRole('button', { name: 'OK', exact: true }).click()

    await expect(jardin(page)).not.toContainText('this slot no longer takes place.')
    await expect(jardin(page)).not.toContainText(nextThursday().label)
    await expect(jardin(page).getByRole('button', { name: 'OK', exact: true })).toHaveCount(0)
  })

  // /home/ui/my-associations/no-registration
  // /home/ui/my-associations/choose
  test("Choose your slots leads to the association's Schedule", async ({ page, request }) => {
    const slug = await withAssociation(page, request)
    await setPeriod(page.request, slug, nextThursday().iso, nextThursday().iso)
    await page.goto('/')

    await jardin(page).getByRole('link', { name: 'Choose your slots' }).click()

    await expect(page).toHaveURL(new RegExp(`/association/${slug}$`))
  })

  // /ui/errors/generic
  test('when the server fails, Confirm shows the generic error message', async ({
    page,
    request,
  }) => {
    await proposedToAlice(page, request)
    await page.route('**/summary/**', (route) => route.fulfill({ status: 500, body: 'failure' }))

    await jardin(page).getByRole('button', { name: 'Confirm', exact: true }).click()

    await expect(page.locator('main').getByText(GENERIC).filter({ visible: true })).toBeVisible()
    await expect(jardin(page)).toContainText('?')
  })
})

test.describe('New association', () => {
  test.beforeEach(async ({ page, request }) => {
    await signedIn(page, request)
    await page.goto('/association/new')
  })

  // /core/ui/new-association/follows
  // /core/model/association/derived
  test('Association identifier follows Name', async ({ page }) => {
    const examples = [
      ['Jardin partagé des Lilas', 'jardin-partage-des-lilas'],
      ['Repair Café  &  Co', 'repair-cafe-co'],
      ['  --Été à Noël!-- ', 'ete-a-noel'],
      ['CAPITALES 2026', 'capitales-2026'],
      ['a'.repeat(60), 'a'.repeat(50)],
      [`${'a'.repeat(49)} bcd`, 'a'.repeat(49)],
      ['!!!', ''],
    ]

    for (const [name, slug] of examples) {
      await nameField(page).fill(name)
      await expect(identifierField(page)).toHaveValue(slug)
    }
  })

  // /core/ui/new-association/follows
  test('once edited, Association identifier no longer follows Name', async ({ page }) => {
    await nameField(page).fill('Jardin')
    await identifierField(page).fill('mon-jardin')

    await nameField(page).fill('Jardin des Lilas')

    await expect(identifierField(page)).toHaveValue('mon-jardin')
  })

  // /core/ui/new-association/enabled
  test('Create association is enabled only when both fields are not empty', async ({ page }) => {
    await expect(createButton(page)).toBeDisabled()

    await nameField(page).fill('Jardin')
    await expect(createButton(page)).toBeEnabled()

    await identifierField(page).fill('')
    await expect(createButton(page)).toBeDisabled()

    await nameField(page).fill('')
    await identifierField(page).fill('jardin')
    await expect(createButton(page)).toBeDisabled()
  })

  // /core/ui/new-association/created
  // /core/operations/create-association/created
  // /home/ui/my-associations/list
  test("creating leads to the new association's Schedule, and My associations lists it as manager", async ({
    page,
  }) => {
    const name = `Jardin ${uniqueSlug()}`
    const slug = name.toLowerCase().replace(' ', '-')

    await nameField(page).fill(name)
    await createButton(page).click()

    await expect(page).toHaveURL(new RegExp(`/association/${slug}$`))
    await page.goto('/')
    const line = page.getByRole('listitem').filter({ hasText: name })
    await expect(line).toContainText(/manager/i)
  })

  // /core/ui/new-association/malformed
  // /ui/errors/kept
  test('a malformed slug shows its message, and what was typed stays', async ({ page }) => {
    await nameField(page).fill('Jardin')
    await identifierField(page).fill('Not A Slug')
    await createButton(page).click()

    await expect(page.getByText(MALFORMED)).toBeVisible()
    await expect(page).toHaveURL(/\/association\/new$/)
    await expect(nameField(page)).toHaveValue('Jardin')
    await expect(identifierField(page)).toHaveValue('Not A Slug')
  })

  // /core/ui/new-association/taken
  test('a taken slug shows its message', async ({ page }) => {
    await nameField(page).fill('Jardin')
    await identifierField(page).fill('new')
    await createButton(page).click()

    await expect(page.getByText(TAKEN)).toBeVisible()
    await expect(page).toHaveURL(/\/association\/new$/)
  })

  // /ui/errors/generic
  // /ui/errors/kept
  test('when the server fails: the generic error message, and what was typed stays', async ({
    page,
  }) => {
    await page.route('**/association/new', (route) =>
      route.request().method() === 'POST'
        ? route.fulfill({ status: 500, body: 'failure' })
        : route.continue(),
    )

    await nameField(page).fill('Jardin')
    await createButton(page).click()

    await expect(page.locator('main').getByText(GENERIC)).toBeVisible()
    await expect(nameField(page)).toHaveValue('Jardin')
    await expect(identifierField(page)).toHaveValue('jardin')
  })
})
