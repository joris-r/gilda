import { expect, test, type Page } from '@playwright/test'

const PASSWORD = 'correct horse'
const MAILPIT_URL = process.env.MAILPIT_URL ?? 'http://localhost:18025'

function uniqueEmail(name: string) {
  return `${name.toLowerCase()}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}@example.org`
}

/** Reads the confirmation link Mailpit caught for `email`, and returns its token. */
async function latestVerificationToken(email: string, timeout = 5000): Promise<string> {
  const deadline = Date.now() + timeout
  while (true) {
    const search = await fetch(
      `${MAILPIT_URL}/api/v1/search?query=${encodeURIComponent(`to:${email}`)}`,
    )
    const { messages } = (await search.json()) as { messages: { ID: string }[] }
    if (messages.length > 0) {
      // Mailpit IDs are ULIDs: sortable by creation time, millisecond precision.
      const latest = messages.reduce((a, b) => (a.ID > b.ID ? a : b))
      const message = await fetch(`${MAILPIT_URL}/api/v1/message/${latest.ID}`)
      const { Text: text } = (await message.json()) as { Text: string }
      const match = /token=([\w-]+)/.exec(text)
      if (!match) throw new Error(`no verification link in the email sent to ${email}`)
      return match[1]
    }
    if (Date.now() > deadline) throw new Error(`no email was sent to ${email}`)
    await new Promise((resolve) => setTimeout(resolve, 200))
  }
}

async function signUp(page: Page, displayName: string, email: string) {
  await page.goto('/')
  await page.getByText('Create an account', { exact: true }).click()
  await page.getByLabel('Display name', { exact: true }).fill(displayName)
  await page.getByLabel('Email', { exact: true }).fill(email)
  await page.getByLabel('Password', { exact: true }).fill(PASSWORD)
  await page.getByRole('button', { name: 'Create account' }).click()
  await expect(page.getByText(email)).toBeVisible()

  const token = await latestVerificationToken(email)
  await page.goto(`/verify-email?token=${token}`)
  await expect(page.getByText('Email confirmed. You can now sign in.')).toBeVisible()

  await signIn(page, email)
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

async function openSchedule(page: Page, association: string) {
  await page.getByText(association, { exact: true }).click()
  await page.getByRole('link', { name: 'Schedule', exact: true }).click()
}

function occurrence(page: Page, dayLabel: string, times: string) {
  return page
    .getByRole('group', { name: dayLabel, exact: true })
    .getByRole('listitem')
    .filter({ hasText: times })
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

  test('the schedule is filled', async ({ page }) => {
    const association = `Jardin partagé ${Date.now()}`
    const chloe = uniqueEmail('Chloe')
    const david = uniqueEmail('David')
    const alice = uniqueEmail('Alice')
    const thursday = dayOfWeek(4, 1)
    const saturday = dayOfWeek(6, 1)
    const closed = dayOfWeek(6, 2)

    await test.step('1. Alice adds the slots and a closure', async () => {
      await signUp(page, 'Alice', alice)
      await page.getByLabel('Name', { exact: true }).fill(association)
      await page.getByRole('button', { name: 'Create association' }).click()
      await addMember(page, 'Chloé', chloe, 'Volunteer')
      await addMember(page, 'David', david, 'Volunteer')
      await page.getByRole('link', { name: 'Opening hours', exact: true }).click()

      const slotForm = page
        .locator('form')
        .filter({ has: page.getByRole('button', { name: 'Add slot' }) })
      for (const weekday of ['Thursday', 'Saturday']) {
        await slotForm.getByRole('combobox', { name: /^Day/ }).selectOption({ label: weekday })
        await slotForm.getByLabel('From').fill('10:00')
        await slotForm.getByLabel('To').fill('13:00')
        await slotForm.getByRole('button', { name: 'Add slot' }).click()
        await expect(page.getByRole('listitem').filter({ hasText: weekday })).toContainText(
          '10:00–13:00',
        )
      }

      const closureForm = page
        .locator('form')
        .filter({ has: page.getByRole('button', { name: 'Add closure' }) })
      await closureForm.getByLabel('From').fill(closed.iso)
      await closureForm.getByLabel('To').fill(closed.iso)
      await closureForm.getByLabel('Label').fill('Fête du quartier')
      await closureForm.getByRole('button', { name: 'Add closure' }).click()
      await expect(page.getByRole('listitem').filter({ hasText: 'Fête du quartier' })).toBeVisible()
      await signOut(page)
    })

    await test.step('2. Chloé sees the closure and signs up for Thursday', async () => {
      await signUp(page, 'Chloé', chloe)
      await openSchedule(page, association)
      const closedDay = page.getByRole('group', {
        name: closed.label,
        exact: true,
      })
      await expect(closedDay).toContainText('Closed')
      await expect(closedDay).toContainText('Fête du quartier')

      await occurrence(page, thursday.label, '10–13').click()
      await page.getByRole('button', { name: 'Sign up', exact: true }).click()
      await expect(occurrence(page, thursday.label, '10–13')).toContainText('Chloé')
      await signOut(page)
    })

    await test.step('3. Alice proposes Saturday to Chloé', async () => {
      await signIn(page, alice)
      await openSchedule(page, association)
      await occurrence(page, saturday.label, '10–13').click()
      await page.getByRole('button', { name: 'Chloé', exact: true }).click()
      await expect(occurrence(page, saturday.label, '10–13')).toContainText(/Chloé\s*\?/)
      await signOut(page)
    })

    await test.step('4. Chloé confirms Saturday and cancels Thursday', async () => {
      await signIn(page, chloe)
      await openSchedule(page, association)
      await occurrence(page, saturday.label, '10–13').click()
      await page.getByRole('button', { name: 'Confirm', exact: true }).click()
      await expect(occurrence(page, saturday.label, '10–13')).not.toContainText('?')
      await expect(occurrence(page, saturday.label, '10–13')).toContainText('Chloé')

      await occurrence(page, thursday.label, '10–13').click()
      await page.getByRole('button', { name: 'Cancel registration…', exact: true }).click()
      await page.getByRole('button', { name: 'Yes, cancel', exact: true }).click()
      await expect(occurrence(page, thursday.label, '10–13').locator('s')).toHaveText('Chloé')
      await signOut(page)
    })

    await test.step('5. David signs up for Thursday, replacing Chloé', async () => {
      await signUp(page, 'David', david)
      await openSchedule(page, association)
      await occurrence(page, thursday.label, '10–13').click()
      await page.getByRole('button', { name: 'Sign up', exact: true }).click()
      await expect(occurrence(page, thursday.label, '10–13')).toContainText('David')
      await expect(occurrence(page, thursday.label, '10–13').locator('s')).toHaveCount(0)
      await expect(occurrence(page, thursday.label, '10–13')).not.toContainText('Chloé')
    })
  })
})
