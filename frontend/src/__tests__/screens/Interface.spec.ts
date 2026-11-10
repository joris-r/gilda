import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mountApp, pageText } from '../mountApp'
import {
  dialog,
  field,
  fill,
  header,
  headersOf,
  item,
  mockApi,
  openUserMenu,
  press,
  showsControl,
  showsField,
  signedOut,
} from '../mockApi'
import { alice, garden, repairCafe, signedInAsAlice } from './fixtures'

function browserPrefers(...languages: string[]) {
  vi.spyOn(navigator, 'languages', 'get').mockReturnValue(languages)
  vi.spyOn(navigator, 'language', 'get').mockReturnValue(languages[0] ?? '')
}

beforeEach(() => {
  localStorage.clear()
  mockApi({
    'GET /api/session': signedInAsAlice,
    'GET /api/associations': {
      status: 200,
      body: [
        { ...garden, role: 'manager', upcoming: [], obsolete: [], planning_period: null },
        { ...repairCafe, role: 'volunteer', upcoming: [], obsolete: [], planning_period: null },
      ],
    },
  })
})

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('Interface language', () => {
  // /ui/language/default
  it('opens in French when the browser prefers French', async () => {
    browserPrefers('fr-FR', 'fr', 'en')

    const wrapper = await mountApp('/')

    expect(pageText(wrapper)).toContain('Mes associations')
    expect(item(wrapper, garden.name).text().toLowerCase()).toContain('responsable')
    expect(item(wrapper, repairCafe.name).text().toLowerCase()).toContain('bénévole')
  })

  // /ui/language/default
  it('opens in English when the browser prefers another language', async () => {
    browserPrefers('de-DE', 'de')

    const text = pageText(await mountApp('/'))

    expect(text).toContain('My associations')
  })

  // /core/ui/header/language
  it('a choice made with the language selector wins over the browser', async () => {
    browserPrefers('fr-FR', 'fr')
    const first = await mountApp('/')

    await openUserMenu(first, 'Alice')
    await field(first, 'Langue').setValue('en')
    first.unmount()
    const second = await mountApp('/')

    expect(pageText(second)).toContain('My associations')
  })
})

describe("An email the user triggers is in the interface's language", () => {
  async function signUpAndResend(interfaceLanguage: 'en' | 'fr') {
    const calls = mockApi({
      'GET /api/session': signedOut,
      'POST /api/accounts': { status: 201, body: alice },
      'POST /api/accounts/verify/resend': { status: 204 },
    })
    const wrapper = await mountApp('/signup')
    await field(wrapper, interfaceLanguage === 'fr' ? 'Language' : 'Langue').setValue(
      interfaceLanguage,
    )
    const french = interfaceLanguage === 'fr'
    await fill(wrapper, french ? 'Nom affiché' : 'Display name', 'Alice')
    await fill(wrapper, french ? 'E-mail' : 'Email', 'alice@example.org')
    await fill(wrapper, french ? 'Mot de passe' : 'Password', 'correct horse')
    await press(wrapper, french ? 'Créer le compte' : 'Create account')
    await press(wrapper, french ? "Renvoyer l'e-mail" : 'Resend the email')
    return calls.filter((call) => call.method === 'POST')
  }

  // /ui/language/emails
  it('in French, the sign-up and resend requests ask for French', async () => {
    browserPrefers('en-GB', 'en')

    const posts = await signUpAndResend('fr')

    expect(posts.map((call) => call.path)).toEqual(['/api/accounts', '/api/accounts/verify/resend'])
    for (const call of posts) expect(headersOf(call).get('Accept-Language')).toBe('fr')
  })

  // /ui/language/emails
  it('in English, the sign-up and resend requests ask for English', async () => {
    browserPrefers('fr-FR', 'fr')

    const posts = await signUpAndResend('en')

    expect(posts).toHaveLength(2)
    for (const call of posts) expect(headersOf(call).get('Accept-Language')).toBe('en')
  })

  // /ui/language/emails
  it('follows the browser preference when no choice was made', async () => {
    browserPrefers('fr-FR', 'fr')
    const calls = mockApi({
      'GET /api/session': signedOut,
      'POST /api/accounts': { status: 201, body: alice },
    })
    const wrapper = await mountApp('/signup')
    await fill(wrapper, 'Nom affiché', 'Alice')
    await fill(wrapper, 'E-mail', 'alice@example.org')
    await fill(wrapper, 'Mot de passe', 'correct horse')

    await press(wrapper, 'Créer le compte')

    const signUp = calls.find((call) => call.path === '/api/accounts')
    expect(signUp && headersOf(signUp).get('Accept-Language')).toBe('fr')
  })
})

describe('Header', () => {
  // /core/ui/header/menu
  it('signed in, the display name opens a menu with the language selector, "Revoke my sign-in link", "Delete my account" and Sign out', async () => {
    const wrapper = await mountApp('/')
    const top = header(wrapper)

    expect(top.text()).toContain('Alice')
    expect(showsField(top, 'Language')).toBe(false)
    expect(showsControl(top, 'Sign out')).toBe(false)
    expect(showsControl(top, 'Revoke my sign-in link')).toBe(false)
    expect(showsControl(top, 'Delete my account')).toBe(false)

    await openUserMenu(wrapper, 'Alice')

    expect(showsField(header(wrapper), 'Language')).toBe(true)
    expect(showsControl(header(wrapper), 'Revoke my sign-in link')).toBe(true)
    expect(showsControl(header(wrapper), 'Delete my account')).toBe(true)
    expect(showsControl(header(wrapper), 'Sign out')).toBe(true)
  })

  // /core/ui/header/revoke
  it('"Revoke my sign-in link" asks for confirmation before calling the API', async () => {
    const calls = mockApi({
      'GET /api/session': signedInAsAlice,
      'GET /api/associations': { status: 200, body: [] },
    })
    const wrapper = await mountApp('/')

    await openUserMenu(wrapper, 'Alice')
    await press(header(wrapper), 'Revoke my sign-in link')

    expect(pageText(wrapper)).toContain(
      'Revoke your sign-in link? Sessions opened with it are signed out.',
    )
    expect(calls.some((c) => c.method === 'DELETE')).toBe(false)

    await press(wrapper, 'Cancel')
    expect(calls.some((c) => c.method === 'DELETE')).toBe(false)
  })

  // /core/ui/header/revoke /core/ui/header/revoked
  it('Confirm revokes the link with DELETE and says so', async () => {
    const calls = mockApi({
      'GET /api/session': signedInAsAlice,
      'GET /api/associations': { status: 200, body: [] },
      'DELETE /api/access-link': { status: 204 },
    })
    const wrapper = await mountApp('/')

    await openUserMenu(wrapper, 'Alice')
    await press(header(wrapper), 'Revoke my sign-in link')
    await press(wrapper, 'Confirm')

    expect(calls).toContainEqual({ method: 'DELETE', path: '/api/access-link', body: undefined })
    expect(pageText(wrapper)).toContain('Your sign-in link is revoked.')
    expect(pageText(wrapper)).toContain('My associations')
  })

  // /core/ui/header/this-session
  it('Confirm leads to Sign in when this session was opened with the link', async () => {
    let revoked = false
    mockApi({
      'GET /api/session': () => (revoked ? signedOut : signedInAsAlice),
      'GET /api/associations': () => (revoked ? signedOut : { status: 200, body: [] }),
      'DELETE /api/access-link': () => {
        revoked = true
        return { status: 204 }
      },
    })
    const wrapper = await mountApp('/')

    await openUserMenu(wrapper, 'Alice')
    await press(header(wrapper), 'Revoke my sign-in link')
    await press(wrapper, 'Confirm')

    expect(wrapper.vm.$route.path).toBe('/')
    expect(showsField(wrapper, 'Password')).toBe(true)
  })

  // /core/ui/header/delete
  it('"Delete my account" asks for confirmation before calling the API', async () => {
    const calls = mockApi({
      'GET /api/session': signedInAsAlice,
      'GET /api/associations': { status: 200, body: [] },
    })
    const wrapper = await mountApp('/')

    await openUserMenu(wrapper, 'Alice')
    await press(header(wrapper), 'Delete my account')

    expect(pageText(wrapper)).toContain(
      'Delete your account? You leave all your associations and your upcoming registrations are cancelled. This cannot be undone.',
    )
    expect(calls.some((c) => c.method === 'DELETE')).toBe(false)

    await press(wrapper, 'Cancel')
    expect(calls.some((c) => c.method === 'DELETE')).toBe(false)
    expect(pageText(wrapper)).toContain('My associations')
  })

  // /core/ui/header/delete
  it('confirming deletes the account with DELETE and leads to Sign in', async () => {
    let deleted = false
    const calls = mockApi({
      'GET /api/session': () => (deleted ? signedOut : signedInAsAlice),
      'GET /api/associations': () => (deleted ? signedOut : { status: 200, body: [] }),
      'DELETE /api/accounts/me': () => {
        deleted = true
        return { status: 204 }
      },
    })
    const wrapper = await mountApp('/')

    await openUserMenu(wrapper, 'Alice')
    await press(header(wrapper), 'Delete my account')
    await press(dialog(wrapper), 'Delete my account')

    expect(calls).toContainEqual({ method: 'DELETE', path: '/api/accounts/me', body: undefined })
    expect(wrapper.vm.$route.path).toBe('/')
    expect(showsField(wrapper, 'Password')).toBe(true)
    expect(header(wrapper).text()).not.toContain('Alice')
  })

  // /core/ui/header/language
  it('the language selector switches between English and French', async () => {
    const wrapper = await mountApp('/')

    await openUserMenu(wrapper, 'Alice')
    await field(wrapper, 'Language').setValue('fr')

    expect(pageText(wrapper)).toContain('Mes associations')
  })

  // /core/ui/header/signed-out
  it('signed out, the language selector stands alone', async () => {
    mockApi({ 'GET /api/session': signedOut })

    const wrapper = await mountApp('/')
    const top = header(wrapper)

    expect(showsField(top, 'Language')).toBe(true)
    expect(showsControl(top, 'Sign out')).toBe(false)
  })
})
