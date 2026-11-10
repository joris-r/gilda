import { expect, test, type Page } from '@playwright/test'

const PASSWORD = 'correct horse'
const MAILPIT_URL = process.env.MAILPIT_URL ?? 'http://localhost:18025'

function uniqueEmail(name: string) {
  return `${name.toLowerCase()}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}@example.org`
}

/** Reads the latest link Mailpit caught for `email`, and returns its token. */
async function latestToken(email: string, timeout = 5000): Promise<string> {
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

async function signUp(page: Page, displayName: string, email: string) {
  await page.goto('/')
  await page.getByText('Create an account', { exact: true }).click()
  await page.getByLabel('Display name', { exact: true }).fill(displayName)
  await page.getByLabel('Email', { exact: true }).fill(email)
  await page.getByLabel('Password', { exact: true }).fill(PASSWORD)
  await page.getByRole('button', { name: 'Create account' }).click()
  await expect(page.getByText(email)).toBeVisible()

  const token = await latestToken(email)
  await page.goto(`/verify-email?token=${token}`)
  await expect(page.getByText('My associations')).toBeVisible()
}

async function signIn(page: Page, email: string, password = PASSWORD) {
  await page.goto('/')
  await page.getByLabel('Email', { exact: true }).fill(email)
  await page.getByLabel('Password', { exact: true }).fill(password)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page.getByText('My associations')).toBeVisible()
}

/** Opens the menu of the signed-in user, in the header, then signs out. */
async function signOut(page: Page) {
  await page.locator('header').getByRole('button').first().click()
  await page.getByText('Sign out', { exact: true }).click()
  await expect(page.getByRole('button', { name: 'Sign in' })).toBeVisible()
}

async function addMember(page: Page, displayName: string, email: string, role: string) {
  await page.getByRole('button', { name: 'Add a member' }).click()
  const dialog = page.getByRole('dialog', { name: 'Add a member' })
  await dialog.getByLabel('Display name', { exact: true }).fill(displayName)
  await dialog.getByLabel('Email', { exact: true }).fill(email)
  await dialog.getByRole('combobox', { name: /^Role/ }).selectOption({ label: role })
  await dialog.getByRole('button', { name: 'Add member' }).click()
  await expect(page.getByText(`${displayName} added.`)).toBeVisible()
  await expect(dialog).toBeHidden()
}

/** Opens the edit dialog of the member `displayName` on Members. */
async function editMember(page: Page, displayName: string) {
  await page.getByRole('button', { name: `Edit ${displayName}`, exact: true }).click()
  return page.getByRole('dialog', { name: displayName, exact: true })
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
}

async function createAssociation(page: Page, association: string) {
  await page.getByRole('button', { name: 'New association' }).click()
  await page.getByLabel('Name', { exact: true }).fill(association)
  await page.getByRole('button', { name: 'Create association' }).click()
  await expect(page.locator('header').getByText(association)).toBeVisible()
}

/** The occurrence of a day, by its times ("10–13"), which its aria-label or its body's holds. */
function occurrence(page: Page, dayLabel: string, times: string) {
  const labelled = `[aria-label*="${times}"]`
  return page
    .getByRole('group', { name: dayLabel, exact: true })
    .locator(`li${labelled}, li:has(${labelled})`)
}

test.describe('Scenarios', () => {
  // /scenarios/a-volunteer-becomes-manager
  test('a volunteer becomes manager', async ({ page }) => {
    const association = `Jardin partagé ${Date.now()}`
    const bruno = uniqueEmail('Bruno')
    const chloe = uniqueEmail('Chloe')
    const myLine = page.getByRole('listitem').filter({ hasText: association })

    await test.step('1. Alice creates her account and the association', async () => {
      await signUp(page, 'Alice', uniqueEmail('Alice'))
      await createAssociation(page, association)
    })

    await test.step('2. Alice adds Bruno as manager, Chloé and David as volunteers', async () => {
      await page.getByRole('link', { name: 'Members', exact: true }).click()
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
      await page.getByRole('link', { name: 'Members', exact: true }).click()
      const dialog = await editMember(page, 'Chloé')
      await dialog.getByRole('combobox', { name: /^Role/ }).selectOption({ label: 'Manager' })
      await dialog.getByRole('button', { name: 'Save' }).click()
      await expect(page.getByText('Chloé is now manager.')).toBeVisible()
      await signOut(page)
    })

    await test.step('5. Chloé signs in and finds the association as manager', async () => {
      await signIn(page, chloe)
      await expect(myLine).toContainText(/manager/i)
      await signOut(page)
    })
  })

  // /scenarios/the-schedule-is-filled
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
      await createAssociation(page, association)
      await page.getByRole('link', { name: 'Members', exact: true }).click()
      await addMember(page, 'Chloé', chloe, 'Volunteer')
      await addMember(page, 'David', david, 'Volunteer')
      await page.locator('header').getByRole('link', { name: association }).click()
      await page.getByRole('link', { name: 'Schedule settings', exact: true }).click()

      const slotForm = page.getByRole('dialog', { name: 'Add a slot' })
      for (const weekday of ['Thursday', 'Saturday']) {
        await page.getByRole('button', { name: 'Add a slot' }).click()
        await slotForm.getByRole('combobox', { name: /^Day/ }).selectOption({ label: weekday })
        await slotForm.getByLabel('From').fill('10:00')
        await slotForm.getByLabel('To').fill('13:00')
        await slotForm.getByRole('button', { name: 'Add slot' }).click()
        await expect(page.getByRole('listitem').filter({ hasText: weekday })).toContainText(
          '10:00–13:00',
        )
      }

      await page.getByRole('button', { name: 'Add a closure' }).click()
      const closureForm = page.getByRole('dialog', { name: 'Add a closure' })
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

  // /scenarios/a-forgotten-password
  test('a forgotten password', async ({ page }) => {
    const alice = uniqueEmail('Alice')
    const newPassword = 'battery staple'
    await signUp(page, 'Alice', alice)
    await signOut(page)

    await test.step('1. Alice asks for a reset link from Sign in', async () => {
      await page.getByText('Forgot your password?', { exact: true }).click()
      await page.getByLabel('Email', { exact: true }).fill(alice)
      await page.getByRole('button', { name: 'Send a reset link' }).click()
      await expect(page.getByText(`If ${alice} has an account`)).toBeVisible()
    })

    await test.step('2. Alice opens the link and chooses a new password', async () => {
      await page.waitForTimeout(10) // Mailpit orders by Created, at millisecond precision.
      const token = await latestToken(alice)
      await page.goto(`/reset-password?token=${token}`)
      await page.getByLabel('New password', { exact: true }).fill(newPassword)
      await page.getByRole('button', { name: 'Set password' }).click()
      await expect(page.getByText('My associations')).toBeVisible()
      await signOut(page)
    })

    await test.step('3. Alice signs in with her new password, not her old one', async () => {
      await page.getByLabel('Email', { exact: true }).fill(alice)
      await page.getByLabel('Password', { exact: true }).fill(PASSWORD)
      await page.getByRole('button', { name: 'Sign in' }).click()
      await expect(page.getByText('Wrong email or password.')).toBeVisible()
      await signIn(page, alice, newPassword)
    })
  })

  // /scenarios/a-volunteer-signs-in-by-link
  test('a volunteer signs in by link', async ({ page }) => {
    const association = `Jardin partagé ${Date.now()}`
    const alice = uniqueEmail('Alice')
    const chloe = uniqueEmail('Chloe')
    const chloeLine = page.getByRole('listitem').filter({ hasText: 'Chloé' })
    let link = ''

    await test.step('1. Alice adds Chloé, who shows "not joined yet"', async () => {
      await signUp(page, 'Alice', alice)
      await createAssociation(page, association)
      await page.getByRole('link', { name: 'Members', exact: true }).click()
      await addMember(page, 'Chloé', chloe, 'Volunteer')
      await expect(chloeLine).toContainText('not joined yet')
      await signOut(page)
    })

    await test.step('2. Chloé asks for a link and signs in with it', async () => {
      await page.getByText('Sign in with an email link', { exact: true }).click()
      await page.getByLabel('Email', { exact: true }).fill(chloe)
      await page.getByRole('button', { name: 'Send me a link' }).click()
      await expect(page.getByText(`If ${chloe} is known here`)).toBeVisible()
      link = `/access?token=${await latestToken(chloe)}`
      await page.goto(link)
      await expect(page.getByText('My associations')).toBeVisible()
      await expect(page.getByRole('listitem').filter({ hasText: association })).toContainText(
        /volunteer/i,
      )
      await signOut(page)
    })

    await test.step('3. Chloé opens the link again and is signed in', async () => {
      await page.goto(link)
      await expect(page.getByText('My associations')).toBeVisible()
      await signOut(page)
    })

    await test.step("4. Alice sees Chloé joined and revokes her link", async () => {
      await signIn(page, alice)
      await page.getByText(association, { exact: true }).click()
      await page.getByRole('link', { name: 'Members', exact: true }).click()
      await expect(chloeLine).toContainText('chloe')
      await expect(chloeLine).not.toContainText('not joined yet')
      const dialog = await editMember(page, 'Chloé')
      await dialog.getByRole('button', { name: 'Revoke link' }).click()
      await page.getByRole('button', { name: 'Revoke', exact: true }).click()
      await expect(page.getByText("Chloé's sign-in link is revoked.")).toBeVisible()
      await signOut(page)
    })

    await test.step('5. The link is no longer valid', async () => {
      await page.goto(link)
      await expect(page.getByText('This link is no longer valid.')).toBeVisible()
    })
  })

  // /scenarios/the-schedule-is-shared
  test('the schedule is shared', async ({ page, context }) => {
    const association = `Jardin partagé ${Date.now()}`
    const alice = uniqueEmail('Alice')
    const thursday = dayOfWeek(4, 1)
    let link = ''

    await test.step('1. Alice adds the slot Thursday 10–13 and signs up for it', async () => {
      await signUp(page, 'Alice', alice)
      await createAssociation(page, association)
      await page.getByRole('link', { name: 'Schedule settings', exact: true }).click()
      await page.getByRole('button', { name: 'Add a slot' }).click()
      const slotForm = page.getByRole('dialog', { name: 'Add a slot' })
      await slotForm.getByRole('combobox', { name: /^Day/ }).selectOption({ label: 'Thursday' })
      await slotForm.getByLabel('From').fill('10:00')
      await slotForm.getByLabel('To').fill('13:00')
      await slotForm.getByRole('button', { name: 'Add slot' }).click()
      await expect(page.getByRole('listitem').filter({ hasText: 'Thursday' })).toContainText(
        '10:00–13:00',
      )
      await page.locator('header').getByRole('link', { name: association }).click()
      await occurrence(page, thursday.label, '10–13').click()
      await page.getByRole('button', { name: 'Sign up', exact: true }).click()
      await expect(occurrence(page, thursday.label, '10–13')).toContainText('Alice')
    })

    await test.step('2. Alice creates a share link and copies it', async () => {
      await context.grantPermissions(['clipboard-read', 'clipboard-write'])
      await page.getByRole('link', { name: 'Schedule settings', exact: true }).click()
      await page.getByRole('button', { name: 'Create a share link' }).click()
      await page.getByRole('button', { name: 'Copy', exact: true }).click()
      await expect(page.getByText('Link copied.')).toBeVisible()
      link = await page.evaluate(() => navigator.clipboard.readText())
      expect(link).toContain('/shared/')
      await signOut(page)
    })

    await test.step('3. Signed out, the link shows her name on Thursday', async () => {
      await page.goto(link)
      await expect(page.locator('header')).toContainText(association)
      await expect(occurrence(page, thursday.label, '10–13')).toContainText('Alice')
    })

    await test.step('4. Alice revokes the share link', async () => {
      await signIn(page, alice)
      await page.getByText(association, { exact: true }).click()
      await page.getByRole('link', { name: 'Schedule settings', exact: true }).click()
      await page.getByRole('button', { name: 'Revoke the share link' }).click()
      await page.getByRole('button', { name: 'Revoke', exact: true }).click()
      await expect(page.getByRole('button', { name: 'Copy', exact: true })).toBeHidden()
      await signOut(page)
    })

    await test.step('5. The link is no longer valid', async () => {
      await page.goto(link)
      await expect(page.getByText('This link is no longer valid.')).toBeVisible()
    })
  })
})
