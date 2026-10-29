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
  it('confirms the token from the link and says sign-in is now possible', async () => {
    const calls = mockApi({
      'GET /api/session': signedOut,
      'POST /api/accounts/verify': { status: 200, body: alice },
    })

    const wrapper = await mountApp('/verify-email?token=abc123')

    expect(calls).toContainEqual({
      method: 'POST',
      path: '/api/accounts/verify',
      body: { token: 'abc123' },
    })
    expect(pageText(wrapper)).toContain('Email confirmed. You can now sign in.')
  })

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
