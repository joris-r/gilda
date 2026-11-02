import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mountApp, pageText } from '../mountApp'
import { fill, mockApi, press, showsField, signedOut } from '../mockApi'
import { alice } from './fixtures'

beforeEach(() => {
  localStorage.clear()
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('Reset password', () => {
  it('is shown signed out, without Sign in', async () => {
    mockApi({ 'GET /api/session': signedOut })

    const wrapper = await mountApp('/reset-password?token=abc123')

    expect(pageText(wrapper)).toContain('Choose a new password')
    expect(showsField(wrapper, 'New password')).toBe(true)
    expect(pageText(wrapper)).not.toContain('No account yet?')
  })

  it('sets the password with the link token and leads to My associations, signed in', async () => {
    let reset = false
    const calls = mockApi({
      'GET /api/session': () => (reset ? { status: 200, body: alice } : signedOut),
      'POST /api/accounts/password-reset/confirm': () => {
        reset = true
        return { status: 200, body: { ...alice, superuser: false } }
      },
      'GET /api/associations': { status: 200, body: [] },
    })
    const wrapper = await mountApp('/reset-password?token=abc123')

    await fill(wrapper, 'New password', 'battery staple')
    await press(wrapper, 'Set password')

    expect(calls).toContainEqual({
      method: 'POST',
      path: '/api/accounts/password-reset/confirm',
      body: { token: 'abc123', password: 'battery staple' },
    })
    expect(wrapper.vm.$route.path).toBe('/')
    expect(pageText(wrapper)).toContain('My associations')
    expect(pageText(wrapper)).toContain('Alice')
  })

  it('says the link is no longer valid for an unknown, expired or used token', async () => {
    mockApi({
      'GET /api/session': signedOut,
      'POST /api/accounts/password-reset/confirm': {
        status: 404,
        body: { error: 'Unknown token' },
      },
    })
    const wrapper = await mountApp('/reset-password?token=expired')

    await fill(wrapper, 'New password', 'battery staple')
    await press(wrapper, 'Set password')

    expect(pageText(wrapper)).toContain('This link is no longer valid.')
    await press(wrapper, 'Request a new link')
    expect(wrapper.vm.$route.path).toBe('/forgot-password')
  })
})
