import { expect, test, type APIRequestContext, type Page } from '@playwright/test'
import { PASSWORD, addSlot, createAccount, createAssociation, latestToken, signedIn, uniqueEmail, datastarReady } from './helpers'

// Datastar's first retry comes about one second after a failure; this leaves room for it.
const RETRY_WINDOW = 3000

type Failure = 'network' | 'server'
const FAILURES: Failure[] = ['network', 'server']

/** Makes every send of an action to a path matching `path` fail, on the network or on the
 * server, and counts them. Loading the page itself (GET) goes through. */
async function failEverySend(page: Page, path: RegExp, failure: Failure) {
  const sends = { count: 0 }
  await page.route(
    (url) => path.test(url.pathname),
    (route) => {
      if (route.request().method() !== 'POST') return route.continue()
      sends.count += 1
      return failure === 'network' ? route.abort() : route.fulfill({ status: 500, body: '' })
    },
  )
  return sends
}

/** Waits for `expected` sends, then checks that no other follows. */
async function expectSends(page: Page, sends: { count: number }, expected = 1) {
  await expect.poll(() => sends.count).toBeGreaterThanOrEqual(expected)
  await page.waitForTimeout(RETRY_WINDOW)
  expect(sends.count).toBe(expected)
}

async function fillSignIn(page: Page, email: string, password = PASSWORD) {
  await page.getByLabel('Email', { exact: true }).fill(email)
  await page.getByLabel('Password', { exact: true }).fill(password)
}

/** Alice signs in on `page` and creates an association with a Thursday slot; returns its slug. */
async function associationWithSlot(page: Page, request: APIRequestContext) {
  await signedIn(page, request)
  const slug = await createAssociation(page.request)
  await addSlot(page.request, slug, 'thursday', '10:00', '13:00')
  return slug
}

/** Each trigger: how to reach it, the path its action posts to, and how to fire it. */
type Trigger = {
  name: string
  open: (page: Page, request: APIRequestContext) => Promise<RegExp>
  fire: (page: Page) => Promise<void>
}

const TRIGGERS: Trigger[] = [
  {
    name: 'Sign in',
    open: async (page) => {
      await page.goto('/')
      await datastarReady(page)
      await fillSignIn(page, uniqueEmail('Nobody'))
      return /^\/sign-in$/
    },
    fire: (page) => page.getByRole('button', { name: 'Sign in' }).click(),
  },
  {
    name: 'Sign out',
    open: async (page, request) => {
      await signedIn(page, request)
      return /^\/sign-out$/
    },
    fire: async (page) => {
      await page.locator('header').getByRole('button', { name: 'Alice' }).click()
      await page.getByRole('button', { name: 'Sign out' }).click()
    },
  },
  {
    name: 'the language selector',
    open: async (page) => {
      await page.goto('/')
      await datastarReady(page)
      return /^\/language$/
    },
    fire: (page) => page.getByLabel('Language').selectOption({ label: 'Français' }),
  },
  {
    name: 'Create account',
    open: async (page) => {
      await page.goto('/signup')
      await datastarReady(page)
      await page.getByLabel('Display name', { exact: true }).fill('Alice')
      await fillSignIn(page, uniqueEmail('Alice'))
      return /^\/signup$/
    },
    fire: (page) => page.getByRole('button', { name: 'Create account' }).click(),
  },
  {
    name: 'Resend the email',
    open: async (page) => {
      await page.goto('/signup')
      await datastarReady(page)
      await page.getByLabel('Display name', { exact: true }).fill('Alice')
      await fillSignIn(page, uniqueEmail('Alice'))
      await page.getByRole('button', { name: 'Create account' }).click()
      await expect(page.getByRole('button', { name: 'Resend the email' })).toBeVisible()
      return /^\/signup\/resend$/
    },
    fire: (page) => page.getByRole('button', { name: 'Resend the email' }).click(),
  },
  {
    name: 'Send a reset link',
    open: async (page) => {
      await page.goto('/forgot-password')
      await datastarReady(page)
      await page.getByLabel('Email', { exact: true }).fill(uniqueEmail('Nobody'))
      return /^\/forgot-password$/
    },
    fire: (page) => page.getByRole('button', { name: 'Send a reset link' }).click(),
  },
  {
    name: 'Set password',
    open: async (page, request) => {
      const email = await createAccount(request)
      expect((await request.post('/forgot-password', { data: { email } })).status()).toBe(200)
      await page.goto(`/reset-password?token=${await latestToken(email)}`)
      await datastarReady(page)
      await page.getByLabel('New password', { exact: true }).fill('another horse')
      return /^\/reset-password$/
    },
    fire: (page) => page.getByRole('button', { name: 'Set password' }).click(),
  },
  {
    name: 'Send me a link',
    open: async (page) => {
      await page.goto('/sign-in-link')
      await datastarReady(page)
      await page.getByLabel('Email', { exact: true }).fill(uniqueEmail('Nobody'))
      return /^\/sign-in-link$/
    },
    fire: (page) => page.getByRole('button', { name: 'Send me a link' }).click(),
  },
  {
    name: 'My preferences: a selector',
    open: async (page, request) => {
      const slug = await associationWithSlot(page, request)
      await page.goto(`/association/${slug}/availability`)
      await datastarReady(page)
      return new RegExp(`^/association/${slug}/availability/preferences/`)
    },
    fire: (page) =>
      page.locator('main').getByRole('listitem').filter({ hasText: 'Thursday' }).getByRole('combobox').selectOption({ label: 'Preferred' }),
  },
  // The triggers below already send their operation once; one of each kind stands for the others.
  {
    name: "Members' preferences: a selector",
    open: async (page, request) => {
      const slug = await associationWithSlot(page, request)
      await page.goto(`/association/${slug}/settings`)
      await datastarReady(page)
      return new RegExp(`^/association/${slug}/settings/preferences/`)
    },
    fire: (page) =>
      page
        .locator('main section')
        .filter({ has: page.getByRole('heading', { name: "Members' preferences" }) })
        .getByRole('row')
        .filter({ hasText: 'Alice' })
        .getByRole('combobox')
        .first()
        .selectOption({ label: 'Preferred' }),
  },
  {
    name: 'Add an absence, in its dialog',
    open: async (page, request) => {
      await signedIn(page, request)
      const slug = await createAssociation(page.request)
      await page.goto(`/association/${slug}/availability`)
      await datastarReady(page)
      await page.getByRole('button', { name: 'Add an absence' }).click()
      const dialog = page.getByRole('dialog', { name: 'Add an absence' })
      await dialog.getByLabel('From', { exact: true }).fill('2099-03-02')
      await dialog.getByLabel('To', { exact: true }).fill('2099-03-06')
      return new RegExp(`^/association/${slug}/availability/absences$`)
    },
    fire: (page) => page.getByRole('dialog', { name: 'Add an absence' }).getByRole('button', { name: 'Add absence' }).click(),
  },
  {
    name: 'Delete my account, in its confirmation',
    open: async (page, request) => {
      await signedIn(page, request)
      await page.locator('header').getByRole('button', { name: 'Alice' }).click()
      await page.getByRole('button', { name: 'Delete my account' }).click()
      return /^\/delete-account$/
    },
    fire: (page) => page.getByRole('dialog').getByRole('button', { name: 'Delete my account' }).click(),
  },
]

test.describe('Errors: a trigger sends its operation once', () => {
  for (const trigger of TRIGGERS) {
    for (const failure of FAILURES) {
      // /ui/errors/once
      test(`${trigger.name}, after a failure on the ${failure}`, async ({ page, request }) => {
        const path = await trigger.open(page, request)
        const sends = await failEverySend(page, path, failure)

        await trigger.fire(page)

        await expectSends(page, sends)
      })
    }
  }

  // /ui/errors/once
  test('Sign in, after a refusal', async ({ page }) => {
    let sends = 0
    page.on('request', (sent) => {
      if (sent.method() === 'POST' && new URL(sent.url()).pathname === '/sign-in') sends += 1
    })
    await page.goto('/')
    await datastarReady(page)
    await fillSignIn(page, uniqueEmail('Nobody'), 'not the password')

    await page.getByRole('button', { name: 'Sign in' }).click()

    await expect(page.getByText('Wrong email or password.')).toBeVisible()
    await page.waitForTimeout(RETRY_WINDOW)
    expect(sends).toBe(1)
  })

  // /ui/errors/once
  test('Sign in, triggered again after a failure, sends again', async ({ page }) => {
    await page.goto('/')
    await datastarReady(page)
    await fillSignIn(page, uniqueEmail('Nobody'))
    const sends = await failEverySend(page, /^\/sign-in$/, 'network')
    await page.getByRole('button', { name: 'Sign in' }).click()
    await expectSends(page, sends)

    await page.getByRole('button', { name: 'Sign in' }).click()

    await expectSends(page, sends, 2)
  })

  for (const failure of FAILURES) {
    // /ui/errors/once
    test(`Access link, opened, after a failure on the ${failure}`, async ({ page }) => {
      const sends = await failEverySend(page, /^\/access$/, failure)

      await page.goto('/access?token=unknown-token')
      await datastarReady(page)

      await expectSends(page, sends)
    })

    // /ui/errors/once
    test(`Confirm email, opened, after a failure on the ${failure}`, async ({ page }) => {
      const sends = await failEverySend(page, /^\/verify-email$/, failure)

      await page.goto('/verify-email?token=unknown-token')
      await datastarReady(page)

      await expectSends(page, sends)
    })
  }

  // /ui/errors/once
  test('Access link, opened again after a failure, sends again', async ({ page }) => {
    const sends = await failEverySend(page, /^\/access$/, 'network')
    await page.goto('/access?token=unknown-token')
    await datastarReady(page)
    await expectSends(page, sends)

    await page.reload()

    await datastarReady(page)

    await expectSends(page, sends, 2)
  })
})
