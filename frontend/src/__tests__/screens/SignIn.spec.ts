import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mountApp, pageText } from '../mountApp'
import { field, fill, mockApi, press, signedOut } from '../mockApi'
import { alice } from './fixtures'

beforeEach(() => {
  localStorage.clear()
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('Sign in', () => {
  it('is shown at / when signed out', async () => {
    mockApi({ 'GET /api/session': signedOut })

    const wrapper = await mountApp('/')

    expect(pageText(wrapper)).toContain('Sign in')
    expect(field(wrapper, 'Email').exists()).toBe(true)
    expect(field(wrapper, 'Password').exists()).toBe(true)
    expect(pageText(wrapper)).toContain('No account yet? Create an account')
  })

  it('signs in with POST /api/session and shows My associations', async () => {
    let signedIn = false
    const calls = mockApi({
      'GET /api/session': () => (signedIn ? { status: 200, body: alice } : signedOut),
      'POST /api/session': () => {
        signedIn = true
        return { status: 200, body: alice }
      },
      'GET /api/associations': { status: 200, body: [] },
    })
    const wrapper = await mountApp('/')

    await fill(wrapper, 'Email', 'alice@example.org')
    await fill(wrapper, 'Password', 'correct horse')
    await press(wrapper, 'Sign in')

    expect(calls).toContainEqual({
      method: 'POST',
      path: '/api/session',
      body: { email: 'alice@example.org', password: 'correct horse' },
    })
    expect(pageText(wrapper)).toContain('My associations')
  })

  it('shows "Wrong email or password." on wrong credentials', async () => {
    mockApi({
      'GET /api/session': signedOut,
      'POST /api/session': { status: 401, body: { error: 'Wrong credentials' } },
    })
    const wrapper = await mountApp('/')

    await fill(wrapper, 'Email', 'alice@example.org')
    await fill(wrapper, 'Password', 'wrong one')
    await press(wrapper, 'Sign in')

    expect(pageText(wrapper)).toContain('Wrong email or password.')
  })

  it('"Create an account" leads to /signup', async () => {
    mockApi({ 'GET /api/session': signedOut })
    const wrapper = await mountApp('/')

    await press(wrapper, 'Create an account')

    expect(wrapper.vm.$route.path).toBe('/signup')
    expect(field(wrapper, 'Display name').exists()).toBe(true)
  })

  it('is shown on an association page when signed out', async () => {
    mockApi({ 'GET /api/session': signedOut })

    const wrapper = await mountApp('/associations/a-garden')

    expect(field(wrapper, 'Password').exists()).toBe(true)
    expect(pageText(wrapper)).toContain('No account yet?')
  })
})
