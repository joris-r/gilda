import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mountApp, pageText } from '../mountApp'
import { fill, mockApi, press, signedOut } from '../mockApi'
import { alice } from './fixtures'

beforeEach(() => {
  localStorage.clear()
})

afterEach(() => {
  vi.unstubAllGlobals()
})

async function fillTheForm(wrapper: Parameters<typeof fill>[0]) {
  await fill(wrapper, 'Display name', 'Alice')
  await fill(wrapper, 'Email', 'alice@example.org')
  await fill(wrapper, 'Password', 'correct horse')
}

describe('Create an account', () => {
  it('is shown at /signup', async () => {
    mockApi({ 'GET /api/session': signedOut })

    const text = pageText(await mountApp('/signup'))

    expect(text).toContain('Create an account')
    expect(text).toContain('Already have an account? Sign in')
  })

  it('creates the account with POST /api/accounts but does not sign in', async () => {
    const calls = mockApi({
      'GET /api/session': signedOut,
      'POST /api/accounts': { status: 201, body: alice },
    })
    const wrapper = await mountApp('/signup')

    await fillTheForm(wrapper)
    await press(wrapper, 'Create account')

    expect(calls).toContainEqual({
      method: 'POST',
      path: '/api/accounts',
      body: { display_name: 'Alice', email: 'alice@example.org', password: 'correct horse' },
    })
    expect(pageText(wrapper)).not.toContain('My associations')
    expect(pageText(wrapper)).toContain('alice@example.org')
  })

  it('offers to resend the confirmation email', async () => {
    const calls = mockApi({
      'GET /api/session': signedOut,
      'POST /api/accounts': { status: 201, body: alice },
      'POST /api/accounts/verify/resend': { status: 204 },
    })
    const wrapper = await mountApp('/signup')
    await fillTheForm(wrapper)
    await press(wrapper, 'Create account')

    await press(wrapper, 'Resend the email')

    expect(calls).toContainEqual({
      method: 'POST',
      path: '/api/accounts/verify/resend',
      body: { email: 'alice@example.org' },
    })
    expect(pageText(wrapper)).toContain('Email sent.')
  })

  it('says so when the email already has an account', async () => {
    mockApi({
      'GET /api/session': signedOut,
      'POST /api/accounts': { status: 409, body: { error: 'Email taken' } },
    })
    const wrapper = await mountApp('/signup')

    await fillTheForm(wrapper)
    await press(wrapper, 'Create account')

    expect(pageText(wrapper)).toContain(
      'An account already exists for this email. Sign in instead.',
    )
  })

  it('says so when the confirmation email cannot be sent', async () => {
    mockApi({
      'GET /api/session': signedOut,
      'POST /api/accounts': { status: 503, body: { error: 'Email not sent' } },
    })
    const wrapper = await mountApp('/signup')

    await fillTheForm(wrapper)
    await press(wrapper, 'Create account')

    expect(pageText(wrapper)).toContain("We couldn't send the confirmation email. Try again later.")
  })

  it('"Sign in" leads to Sign in', async () => {
    mockApi({ 'GET /api/session': signedOut })
    const wrapper = await mountApp('/signup')

    await press(wrapper, 'Sign in')

    expect(wrapper.vm.$route.path).toBe('/')
    expect(pageText(wrapper)).toContain('No account yet?')
  })
})
