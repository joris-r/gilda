import { expect, test, type Page } from '@playwright/test'

const PASSWORD = 'correct horse'

function uniqueEmail(name: string) {
  return `${name.toLowerCase()}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}@example.org`
}

async function signUp(page: Page, displayName: string, email: string) {
  await page.goto('/')
  await page.getByText('Create an account', { exact: true }).click()
  await page.getByLabel('Display name', { exact: true }).fill(displayName)
  await page.getByLabel('Email', { exact: true }).fill(email)
  await page.getByLabel('Password', { exact: true }).fill(PASSWORD)
  await page.getByRole('button', { name: 'Create account' }).click()
  await expect(page.getByText('My associations')).toBeVisible()
}

async function addMember(page: Page, displayName: string, email: string) {
  await page.getByLabel('Display name', { exact: true }).fill(displayName)
  await page.getByLabel('Email', { exact: true }).fill(email)
  await page.getByRole('button', { name: 'Add member' }).click()
  await expect(page.getByText(`${displayName} added.`)).toBeVisible()
}

test.describe('Associations', () => {
  test('a manager creates an association, adds members and promotes one', async ({ page }) => {
    const association = `Jardin partagé ${Date.now()}`
    await signUp(page, 'Alice', uniqueEmail('Alice'))

    await page.getByLabel('Name', { exact: true }).fill(association)
    await page.getByRole('button', { name: 'Create association' }).click()
    await expect(page.getByRole('heading', { name: association })).toBeVisible()

    await addMember(page, 'Bruno', uniqueEmail('Bruno'))
    await addMember(page, 'Chloé', uniqueEmail('Chloe'))
    const bruno = page.getByRole('listitem').filter({ hasText: 'Bruno' })
    await expect(bruno).toContainText(/volunteer/i)

    await bruno.getByText('Change role', { exact: true }).click()
    await expect(bruno).toContainText('Make Bruno manager?')
    await bruno.getByText('Confirm', { exact: true }).click()

    await expect(page.getByText('Bruno is now manager.')).toBeVisible()
    await expect(bruno).toContainText(/manager/i)
  })

  test('a volunteer added by email signs up and finds the association', async ({ browser }) => {
    const association = `Repair Café ${Date.now()}`
    const chloeEmail = uniqueEmail('Chloe')

    const manager = await browser.newPage()
    await signUp(manager, 'Alice', uniqueEmail('Alice'))
    await manager.getByLabel('Name', { exact: true }).fill(association)
    await manager.getByRole('button', { name: 'Create association' }).click()
    await addMember(manager, 'Chloé', chloeEmail)
    await expect(manager.getByRole('listitem').filter({ hasText: 'Chloé' })).toContainText(
      'no account',
    )

    const volunteer = await browser.newPage()
    await signUp(volunteer, 'Chloé', chloeEmail)
    const line = volunteer.getByRole('listitem').filter({ hasText: association })
    await expect(line).toContainText(/volunteer/i)

    await line.getByText(association, { exact: true }).click()
    await expect(volunteer.getByRole('heading', { name: association })).toBeVisible()
    await expect(volunteer.getByText('Change role')).toHaveCount(0)
    await expect(volunteer.getByText('Add a member')).toHaveCount(0)
  })

  test('signing out leads back to Sign in, and signing in again works', async ({ page }) => {
    const email = uniqueEmail('Alice')
    await signUp(page, 'Alice', email)

    await page.getByText('Sign out', { exact: true }).click()
    await expect(page.getByRole('button', { name: 'Sign in' })).toBeVisible()

    await page.getByLabel('Email', { exact: true }).fill(email)
    await page.getByLabel('Password', { exact: true }).fill(PASSWORD)
    await page.getByRole('button', { name: 'Sign in' }).click()
    await expect(page.getByText('My associations')).toBeVisible()
  })
})
