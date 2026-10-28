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

async function signIn(page: Page, email: string) {
  await page.goto('/')
  await page.getByLabel('Email', { exact: true }).fill(email)
  await page.getByLabel('Password', { exact: true }).fill(PASSWORD)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page.getByText('My associations')).toBeVisible()
}

async function signOut(page: Page) {
  await page.getByText('Sign out', { exact: true }).click()
  await expect(page.getByRole('button', { name: 'Sign in' })).toBeVisible()
}

async function addMember(page: Page, displayName: string, email: string, role: string) {
  await page.getByLabel('Display name', { exact: true }).fill(displayName)
  await page.getByLabel('Email', { exact: true }).fill(email)
  await page.getByRole('combobox', { name: /^Role/ }).selectOption({ label: role })
  await page.getByRole('button', { name: 'Add member' }).click()
  await expect(page.getByText(`${displayName} added.`)).toBeVisible()
}

test.describe('Scenarios', () => {
  test('a volunteer becomes manager', async ({ page }) => {
    const association = `Jardin partagé ${Date.now()}`
    const bruno = uniqueEmail('Bruno')
    const chloe = uniqueEmail('Chloe')
    const myLine = page.getByRole('listitem').filter({ hasText: association })

    await test.step('1. Alice creates her account and the association', async () => {
      await signUp(page, 'Alice', uniqueEmail('Alice'))
      await page.getByLabel('Name', { exact: true }).fill(association)
      await page.getByRole('button', { name: 'Create association' }).click()
      await expect(page.getByRole('heading', { name: association })).toBeVisible()
    })

    await test.step('2. Alice adds Bruno as manager, Chloé and David as volunteers', async () => {
      await addMember(page, 'Bruno', bruno, 'Manager')
      await addMember(page, 'Chloé', chloe, 'Volunteer')
      await addMember(page, 'David', uniqueEmail('David'), 'Volunteer')
      await signOut(page)
    })

    await test.step('3. Chloé creates her account and finds the association as volunteer', async () => {
      await signUp(page, 'Chloé', chloe)
      await expect(myLine).toContainText(/volunteer/i)
      await signOut(page)
    })

    await test.step('4. Bruno creates his account and promotes Chloé', async () => {
      await signUp(page, 'Bruno', bruno)
      await myLine.getByText(association, { exact: true }).click()
      const chloeLine = page.getByRole('listitem').filter({ hasText: 'Chloé' })
      await chloeLine.getByText('Change role', { exact: true }).click()
      await chloeLine.getByText('Confirm', { exact: true }).click()
      await expect(page.getByText('Chloé is now manager.')).toBeVisible()
      await signOut(page)
    })

    await test.step('5. Chloé signs in and finds the association as manager', async () => {
      await signIn(page, chloe)
      await expect(myLine).toContainText(/manager/i)
      await signOut(page)
    })
  })
})
