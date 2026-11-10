import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mountApp, pageText } from '../mountApp'
import { fill, mockApi, press, showsField, signedOut } from '../mockApi'

beforeEach(() => {
  localStorage.clear()
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('Forgot password', () => {
  // /core/ui/access/signed-out /core/ui/forgot-password/form
  it('is shown signed out, without Sign in', async () => {
    mockApi({ 'GET /api/session': signedOut })

    const wrapper = await mountApp('/forgot-password')

    expect(pageText(wrapper)).toContain('Forgot your password?')
    expect(showsField(wrapper, 'Email')).toBe(true)
    expect(showsField(wrapper, 'Password')).toBe(false)
  })

  // /core/ui/forgot-password/send
  it('asks for a reset link and says where it was sent, instead of the form', async () => {
    const calls = mockApi({
      'GET /api/session': signedOut,
      'POST /api/accounts/password-reset': { status: 204 },
    })
    const wrapper = await mountApp('/forgot-password')

    await fill(wrapper, 'Email', 'alice@example.org')
    await press(wrapper, 'Send a reset link')

    expect(calls).toContainEqual({
      method: 'POST',
      path: '/api/accounts/password-reset',
      body: { email: 'alice@example.org' },
    })
    expect(pageText(wrapper)).toContain(
      'If alice@example.org has an account, a reset link has been sent to it.',
    )
    expect(showsField(wrapper, 'Email')).toBe(false)
  })

  // /core/ui/forgot-password/form
  it('"Back to Sign in" leads to Sign in', async () => {
    mockApi({ 'GET /api/session': signedOut })
    const wrapper = await mountApp('/forgot-password')

    await press(wrapper, 'Back to Sign in')

    expect(wrapper.vm.$route.path).toBe('/')
    expect(showsField(wrapper, 'Password')).toBe(true)
  })
})
