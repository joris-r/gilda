import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mountApp, pageText } from '../mountApp'
import { mockApi, press, showsField, signedOut } from '../mockApi'
import { alice } from './fixtures'

beforeEach(() => {
  localStorage.clear()
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('Access link', () => {
  it('signs in with the token from the link and leads to My associations', async () => {
    let signedIn = false
    const calls = mockApi({
      'GET /api/session': () => (signedIn ? { status: 200, body: alice } : signedOut),
      'POST /api/session/access-link': () => {
        signedIn = true
        return { status: 200, body: { ...alice, superuser: false } }
      },
      'GET /api/associations': { status: 200, body: [] },
    })

    const wrapper = await mountApp('/access?token=abc123')

    expect(calls).toContainEqual({
      method: 'POST',
      path: '/api/session/access-link',
      body: { token: 'abc123' },
    })
    expect(wrapper.vm.$route.path).toBe('/')
    expect(pageText(wrapper)).toContain('My associations')
    expect(pageText(wrapper)).toContain('Alice')
  })

  it('says the link is no longer valid for an unknown token or a revoked link', async () => {
    mockApi({
      'GET /api/session': signedOut,
      'POST /api/session/access-link': { status: 404, body: { error: 'Unknown token' } },
    })

    const wrapper = await mountApp('/access?token=revoked')

    expect(pageText(wrapper)).toContain('This link is no longer valid.')

    await press(wrapper, 'Sign in with an email link')
    expect(wrapper.vm.$route.path).toBe('/sign-in-link')
    expect(showsField(wrapper, 'Email')).toBe(true)
  })
})
