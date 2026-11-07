import { expect, test, type APIRequestContext, type Page } from '@playwright/test'
import { PASSWORD, latestToken, uniqueEmail } from './helpers'

const GENERIC = 'Something went wrong. Try again.'
const MALFORMED =
  'Use only lowercase letters, digits and hyphens, starting and ending with a letter or a digit.'
const TAKEN = 'This association identifier is already taken.'

async function signIn(page: Page, request: APIRequestContext) {
  const email = uniqueEmail('Alice')
  await request.post('/signup', { data: { displayName: 'Alice', email, password: PASSWORD } })
  await request.post('/verify-email', { data: { token: await latestToken(email) } })
  await page.goto('/')
  await page.getByLabel('Email', { exact: true }).fill(email)
  await page.getByLabel('Password', { exact: true }).fill(PASSWORD)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page.locator('header').getByText('My associations')).toBeVisible()
}

function nameField(page: Page) {
  return page.getByLabel('Name', { exact: true })
}

function identifierField(page: Page) {
  return page.getByLabel('Association identifier')
}

function createButton(page: Page) {
  return page.getByRole('button', { name: 'Create association' })
}

function uniqueSlug() {
  return `e2e-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

test.describe('My associations', () => {
  test('New association leads to its screen, and Cancel back', async ({ page, request }) => {
    await signIn(page, request)

    await page.getByRole('link', { name: 'New association' }).click()
    await expect(page).toHaveURL(/\/association\/new$/)
    await expect(page.getByRole('heading', { name: 'New association' })).toBeVisible()

    await page.getByRole('link', { name: 'Cancel' }).click()
    await expect(page).toHaveURL(/\/$/)
    await expect(page.getByText('You are not a member of any association yet.')).toBeVisible()
  })

  test("the header's My associations leads back from New association", async ({
    page,
    request,
  }) => {
    await signIn(page, request)
    await page.goto('/association/new')

    await page.locator('header').getByRole('link', { name: 'My associations' }).click()

    await expect(page).toHaveURL(/\/$/)
  })

  test("a name leads to the association's Schedule", async ({ page, request }) => {
    await signIn(page, request)
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

test.describe('New association', () => {
  test.beforeEach(async ({ page, request }) => {
    await signIn(page, request)
    await page.goto('/association/new')
  })

  test('R35: Association identifier follows Name', async ({ page }) => {
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

  test('R35: once edited, Association identifier no longer follows Name', async ({ page }) => {
    await nameField(page).fill('Jardin')
    await identifierField(page).fill('mon-jardin')

    await nameField(page).fill('Jardin des Lilas')

    await expect(identifierField(page)).toHaveValue('mon-jardin')
  })

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

  test('a malformed slug shows its message, and what was typed stays', async ({ page }) => {
    await nameField(page).fill('Jardin')
    await identifierField(page).fill('Not A Slug')
    await createButton(page).click()

    await expect(page.getByText(MALFORMED)).toBeVisible()
    await expect(page).toHaveURL(/\/association\/new$/)
    await expect(nameField(page)).toHaveValue('Jardin')
    await expect(identifierField(page)).toHaveValue('Not A Slug')
  })

  test('a taken slug shows its message', async ({ page }) => {
    await nameField(page).fill('Jardin')
    await identifierField(page).fill('new')
    await createButton(page).click()

    await expect(page.getByText(TAKEN)).toBeVisible()
    await expect(page).toHaveURL(/\/association\/new$/)
  })

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
