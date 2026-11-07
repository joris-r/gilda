import { expect, test, type APIRequestContext, type Page } from '@playwright/test'
import { PASSWORD, latestToken, uniqueEmail } from './helpers'

const GENERIC = 'Something went wrong. Try again.'

function uniqueSlug() {
  return `e2e-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

/** Alice signs in on `page`, creates an association with `slots`, and opens its My availability. */
async function openAvailability(page: Page, request: APIRequestContext, slots: [string, string, string][]) {
  const alice = uniqueEmail('Alice')
  await request.post('/signup', { data: { displayName: 'Alice', email: alice, password: PASSWORD } })
  await request.post('/verify-email', { data: { token: await latestToken(alice) } })
  await page.goto('/')
  await page.getByLabel('Email', { exact: true }).fill(alice)
  await page.getByLabel('Password', { exact: true }).fill(PASSWORD)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page.locator('header').getByText('My associations')).toBeVisible()
  const slug = uniqueSlug()
  const created = await page.request.post('/api/associations', { data: { name: 'Jardin partagé', slug } })
  expect(created.status()).toBe(201)
  const { id } = (await created.json()) as { id: string }
  for (const [weekday, start, end] of slots) {
    const slot = await page.request.post(`/api/associations/${id}/slots`, { data: { weekday, start, end } })
    expect(slot.status()).toBe(201)
  }
  await page.goto(`/association/${slug}/availability`)
  await expect(page.locator('header').getByText('My availability')).toBeVisible()
  return id
}

function selector(page: Page, text: string) {
  return page.locator('main').getByRole('listitem').filter({ hasText: text }).getByRole('combobox')
}

/** Waits for the preference saved on a slot to be `value`, or none when `value` is null. */
async function expectSaved(page: Page, id: string, value: string | null) {
  await expect
    .poll(async () => {
      const response = await page.request.get(`/api/associations/${id}/preferences`)
      const preferences = (await response.json()) as { value: string }[]
      return preferences.map((p) => p.value)
    })
    .toEqual(value === null ? [] : [value])
}

test.describe('My availability: My preferences', () => {
  test('each slot has a selector showing "—"', async ({ page, request }) => {
    await openAvailability(page, request, [
      ['thursday', '10:00', '13:00'],
      ['saturday', '10:00', '13:00'],
    ])

    await expect(selector(page, 'Thursday 10:00–13:00')).toHaveValue('')
    await expect(selector(page, 'Saturday 10:00–13:00')).toHaveValue('')
  })

  test('choosing a value saves it at once', async ({ page, request }) => {
    const id = await openAvailability(page, request, [['thursday', '10:00', '13:00']])

    await selector(page, 'Thursday').selectOption({ label: 'Preferred' })

    await expectSaved(page, id, 'preferred')
    await page.reload()
    await expect(selector(page, 'Thursday')).toHaveValue('preferred')
  })

  test('choosing another value replaces it', async ({ page, request }) => {
    const id = await openAvailability(page, request, [['thursday', '10:00', '13:00']])
    await selector(page, 'Thursday').selectOption({ label: 'Preferred' })
    await expectSaved(page, id, 'preferred')

    await selector(page, 'Thursday').selectOption({ label: 'Unavailable' })

    await expectSaved(page, id, 'unavailable')
  })

  test('"—" deletes it', async ({ page, request }) => {
    const id = await openAvailability(page, request, [['thursday', '10:00', '13:00']])
    await selector(page, 'Thursday').selectOption({ label: 'Possible' })
    await expectSaved(page, id, 'possible')

    await selector(page, 'Thursday').selectOption({ label: '—' })

    await expectSaved(page, id, null)
    await page.reload()
    await expect(selector(page, 'Thursday')).toHaveValue('')
  })

  test('each selector saves its own slot', async ({ page, request }) => {
    await openAvailability(page, request, [
      ['thursday', '10:00', '13:00'],
      ['saturday', '10:00', '13:00'],
    ])

    await selector(page, 'Saturday').selectOption({ label: 'Possible' })
    await selector(page, 'Thursday').selectOption({ label: 'Unavailable' })

    await expect(async () => {
      await page.reload()
      await expect(selector(page, 'Thursday')).toHaveValue('unavailable', { timeout: 1000 })
      await expect(selector(page, 'Saturday')).toHaveValue('possible', { timeout: 1000 })
    }).toPass()
  })

  test('when the server fails: the generic error', async ({ page, request }) => {
    await openAvailability(page, request, [['thursday', '10:00', '13:00']])
    await page.route('**/availability/preferences/**', (route) => route.fulfill({ status: 500, body: 'failure' }))

    await selector(page, 'Thursday').selectOption({ label: 'Preferred' })

    await expect(page.locator('main').getByText(GENERIC)).toBeVisible()
  })
})
