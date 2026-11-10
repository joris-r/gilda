import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mountApp, pageText } from '../mountApp'
import { fill, mockApi, press, showsField, signedOut } from '../mockApi'

beforeEach(() => {
  localStorage.clear()
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('Sign-in link', () => {
  // /core/ui/access/signed-out /core/ui/sign-in-link/form
  it('is shown signed out, without Sign in', async () => {
    mockApi({ 'GET /api/session': signedOut })

    const wrapper = await mountApp('/sign-in-link')

    expect(pageText(wrapper)).toContain('Sign in with an email link')
    expect(showsField(wrapper, 'Email')).toBe(true)
    expect(showsField(wrapper, 'Password')).toBe(false)
  })

  // /core/ui/sign-in-link/send
  it('asks for the link and says where it was sent, instead of the form', async () => {
    const calls = mockApi({
      'GET /api/session': signedOut,
      'POST /api/access-link': { status: 204 },
    })
    const wrapper = await mountApp('/sign-in-link')

    await fill(wrapper, 'Email', 'alice@example.org')
    await press(wrapper, 'Send me a link')

    expect(calls).toContainEqual({
      method: 'POST',
      path: '/api/access-link',
      body: { email: 'alice@example.org' },
    })
    expect(pageText(wrapper)).toContain(
      'If alice@example.org is known here, a sign-in link has been sent to it.',
    )
    expect(showsField(wrapper, 'Email')).toBe(false)
  })

  // /core/ui/sign-in-link/form
  it('"Back to Sign in" leads to Sign in', async () => {
    mockApi({ 'GET /api/session': signedOut })
    const wrapper = await mountApp('/sign-in-link')

    await press(wrapper, 'Back to Sign in')

    expect(wrapper.vm.$route.path).toBe('/')
    expect(showsField(wrapper, 'Password')).toBe(true)
  })
})
