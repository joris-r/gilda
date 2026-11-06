import { expect, test, type Page } from '@playwright/test'
import { PASSWORD, latestToken, uniqueEmail } from './helpers'

const GENERIC = 'Something went wrong. Try again.'

async function fillSignUp(page: Page, displayName: string, email: string, password = PASSWORD) {
  await page.getByLabel('Display name', { exact: true }).fill(displayName)
  await page.getByLabel('Email', { exact: true }).fill(email)
  await page.getByLabel('Password', { exact: true }).fill(password)
}

async function submitSignUp(page: Page, displayName: string, email: string) {
  await fillSignUp(page, displayName, email)
  await page.getByRole('button', { name: 'Create account' }).click()
}

test.describe('Create an account', () => {
  test('Sign in leads to it, and it leads back to Sign in', async ({ page }) => {
    await page.goto('/')

    await page.getByRole('link', { name: 'Create an account' }).click()
    await expect(page.getByRole('heading', { name: 'Create an account' })).toBeVisible()

    await page.getByRole('link', { name: 'Sign in' }).click()
    await expect(page.getByRole('button', { name: 'Sign in' })).toBeVisible()
  })

  test('success replaces the form with the message', async ({ page }) => {
    const email = uniqueEmail('Alice')
    await page.goto('/signup')

    await submitSignUp(page, 'Alice', email)

    await expect(page.getByText(`Check ${email} for a confirmation link.`)).toBeVisible()
    await expect(page.getByRole('button', { name: 'Create account' })).toBeHidden()
  })

  test('Resend the email shows "Email sent." and the new link works', async ({ page }) => {
    const email = uniqueEmail('Alice')
    await page.goto('/signup')
    await submitSignUp(page, 'Alice', email)
    await expect(page.getByText(`Check ${email} for a confirmation link.`)).toBeVisible()
    const first = await latestToken(email)

    await page.getByRole('button', { name: 'Resend the email' }).click()

    await expect(page.getByText('Email sent.')).toBeVisible()
    await expect.poll(() => latestToken(email)).not.toBe(first)
    await page.goto(`/verify-email?token=${await latestToken(email)}`)
    await expect(page.getByText('My associations')).toBeVisible()
  })

  test('a refused account keeps the form and what was typed', async ({ page, request }) => {
    const email = uniqueEmail('Alice')
    await request.post('/signup', {
      data: { displayName: 'Alice', email, password: PASSWORD },
    })
    await request.post('/verify-email', { data: { token: await latestToken(email) } })
    await page.goto('/signup')

    await submitSignUp(page, 'Other', email)

    await expect(
      page.getByText('An account already exists for this email. Sign in instead.'),
    ).toBeVisible()
    await expect(page.getByLabel('Display name', { exact: true })).toHaveValue('Other')
    await expect(page.getByLabel('Email', { exact: true })).toHaveValue(email)
  })

  test('the browser refuses a password of fewer than 8 characters', async ({ page }) => {
    const email = uniqueEmail('Alice')
    await page.goto('/signup')

    await fillSignUp(page, 'Alice', email, '1234567')
    await page.getByRole('button', { name: 'Create account' }).click()

    await expect(page.getByRole('button', { name: 'Create account' })).toBeVisible()
    await expect(page.getByText(`Check ${email} for a confirmation link.`)).toBeHidden()
  })
})

test.describe('Confirm email', () => {
  test('the link signs in and leads to My associations', async ({ page }) => {
    const email = uniqueEmail('Alice')
    await page.goto('/signup')
    await submitSignUp(page, 'Alice', email)
    await expect(page.getByText(`Check ${email} for a confirmation link.`)).toBeVisible()

    await page.goto(`/verify-email?token=${await latestToken(email)}`)

    await expect(page.getByText('My associations')).toBeVisible()
    await expect(page.getByText('Alice')).toBeVisible()
    await expect(page).toHaveURL(/\/$/)
  })

  test('an unknown link shows the message and a way to Create an account', async ({ page }) => {
    await page.goto('/verify-email?token=unknown-token')

    await expect(page.getByText('This link is no longer valid.')).toBeVisible()

    await page.getByRole('link', { name: 'Create an account' }).click()
    await expect(page.getByRole('heading', { name: 'Create an account' })).toBeVisible()
  })
})

test.describe('Generic error message', () => {
  test('is hidden until an action fails', async ({ page }) => {
    await page.goto('/')

    await expect(page.getByText(GENERIC)).toBeHidden()
  })

  test('Sign in, when the server fails: shown, and what was typed stays', async ({ page }) => {
    const email = uniqueEmail('Alice')
    await page.route('**/sign-in', (route) => route.fulfill({ status: 500, body: 'failure' }))
    await page.goto('/')

    await page.getByLabel('Email', { exact: true }).fill(email)
    await page.getByLabel('Password', { exact: true }).fill(PASSWORD)
    await page.getByRole('button', { name: 'Sign in' }).click()

    await expect(page.getByText(GENERIC)).toBeVisible()
    await expect(page.getByLabel('Email', { exact: true })).toHaveValue(email)
  })

  test('Sign in, on the way to the server: shown', async ({ page }) => {
    await page.route('**/sign-in', (route) => route.abort())
    await page.goto('/')

    await page.getByLabel('Email', { exact: true }).fill(uniqueEmail('Alice'))
    await page.getByLabel('Password', { exact: true }).fill(PASSWORD)
    await page.getByRole('button', { name: 'Sign in' }).click()

    await expect(page.getByText(GENERIC)).toBeVisible()
  })

  test('Create an account, when the server fails: shown', async ({ page }) => {
    const email = uniqueEmail('Alice')
    await page.route('**/signup', (route) =>
      route.request().method() === 'POST'
        ? route.fulfill({ status: 500, body: 'failure' })
        : route.continue(),
    )
    await page.goto('/signup')

    await submitSignUp(page, 'Alice', email)

    await expect(page.getByText(GENERIC)).toBeVisible()
    await expect(page.getByLabel('Email', { exact: true })).toHaveValue(email)
  })

  test('leaves when the next try gets its own answer', async ({ page }) => {
    await page.route('**/sign-in', (route) => route.fulfill({ status: 500, body: 'failure' }))
    await page.goto('/')
    await page.getByLabel('Email', { exact: true }).fill(uniqueEmail('Nobody'))
    await page.getByLabel('Password', { exact: true }).fill('not the password')
    await page.getByRole('button', { name: 'Sign in' }).click()
    await expect(page.getByText(GENERIC)).toBeVisible()

    await page.unroute('**/sign-in')
    await page.getByRole('button', { name: 'Sign in' }).click()

    await expect(page.getByText('Wrong email or password.')).toBeVisible()
    await expect(page.getByText(GENERIC)).toBeHidden()
  })
})

test.describe('Not found', () => {
  test('shows the page, and its link leads to the home page', async ({ page }) => {
    const response = await page.goto('/nothing-here')

    expect(response?.status()).toBe(404)
    await expect(page.getByRole('heading', { name: 'Page not found' })).toBeVisible()

    await page.getByRole('link', { name: 'Back to the home page' }).click()
    await expect(page.getByRole('button', { name: 'Sign in' })).toBeVisible()
  })

  test('the language selector works on it', async ({ page }) => {
    await page.goto('/nothing-here')

    await page.getByLabel('Language').selectOption({ label: 'Français' })

    await expect(page.getByRole('heading', { name: 'Page introuvable' })).toBeVisible()
  })
})
