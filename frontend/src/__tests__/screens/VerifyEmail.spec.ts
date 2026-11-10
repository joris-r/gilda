import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mountApp, pageText } from '../mountApp'
import { mockApi, press, signedOut } from '../mockApi'
import { alice } from './fixtures'

beforeEach(() => {
  localStorage.clear()
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('Confirm email', () => {
  // /core/ui/confirm-email/confirmed
  it('confirms the token from the link and leads to My associations, signed in', async () => {
    let verified = false
    const calls = mockApi({
      'GET /api/session': () => (verified ? { status: 200, body: alice } : signedOut),
      'POST /api/accounts/verify': () => {
        verified = true
        return { status: 200, body: { ...alice, superuser: false } }
      },
      'GET /api/associations': { status: 200, body: [] },
    })

    const wrapper = await mountApp('/verify-email?token=abc123')

    expect(calls).toContainEqual({
      method: 'POST',
      path: '/api/accounts/verify',
      body: { token: 'abc123' },
    })
    expect(wrapper.vm.$route.path).toBe('/')
    expect(pageText(wrapper)).toContain('My associations')
    expect(pageText(wrapper)).toContain('Alice')
  })

  // /core/ui/confirm-email/invalid
  it('says the link is no longer valid for an unknown or expired token', async () => {
    mockApi({
      'GET /api/session': signedOut,
      'POST /api/accounts/verify': { status: 404, body: { error: 'Unknown token' } },
    })

    const wrapper = await mountApp('/verify-email?token=expired')

    expect(pageText(wrapper)).toContain('This link is no longer valid.')

    await press(wrapper, 'Create an account')
    expect(wrapper.vm.$route.path).toBe('/signup')
  })
})
