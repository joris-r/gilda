import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mountApp, pageText } from '../mountApp'
import {
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
        { ...garden, role: 'manager', upcoming: [], planning_period: null },
        { ...repairCafe, role: 'volunteer', upcoming: [], planning_period: null },
      ],
    },
  })
})

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('Interface language', () => {
  it('opens in French when the browser prefers French', async () => {
    browserPrefers('fr-FR', 'fr', 'en')

    const wrapper = await mountApp('/')

    expect(pageText(wrapper)).toContain('Mes associations')
    expect(item(wrapper, garden.name).text().toLowerCase()).toContain('responsable')
    expect(item(wrapper, repairCafe.name).text().toLowerCase()).toContain('bénévole')
  })

  it('opens in English when the browser prefers another language', async () => {
    browserPrefers('de-DE', 'de')

    const text = pageText(await mountApp('/'))

    expect(text).toContain('My associations')
  })

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

  it('in French, the sign-up and resend requests ask for French', async () => {
    browserPrefers('en-GB', 'en')

    const posts = await signUpAndResend('fr')

    expect(posts.map((call) => call.path)).toEqual(['/api/accounts', '/api/accounts/verify/resend'])
    for (const call of posts) expect(headersOf(call).get('Accept-Language')).toBe('fr')
  })

  it('in English, the sign-up and resend requests ask for English', async () => {
    browserPrefers('fr-FR', 'fr')

    const posts = await signUpAndResend('en')

    expect(posts).toHaveLength(2)
    for (const call of posts) expect(headersOf(call).get('Accept-Language')).toBe('en')
  })

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
  it('signed in, the display name opens a menu with the language selector and Sign out', async () => {
    const wrapper = await mountApp('/')
    const top = header(wrapper)

    expect(top.text()).toContain('Alice')
    expect(showsField(top, 'Language')).toBe(false)
    expect(showsControl(top, 'Sign out')).toBe(false)

    await openUserMenu(wrapper, 'Alice')

    expect(showsField(header(wrapper), 'Language')).toBe(true)
    expect(showsControl(header(wrapper), 'Sign out')).toBe(true)
  })

  it('the language selector switches between English and French', async () => {
    const wrapper = await mountApp('/')

    await openUserMenu(wrapper, 'Alice')
    await field(wrapper, 'Language').setValue('fr')

    expect(pageText(wrapper)).toContain('Mes associations')
  })

  it('signed out, the language selector stands alone', async () => {
    mockApi({ 'GET /api/session': signedOut })

    const wrapper = await mountApp('/')
    const top = header(wrapper)

    expect(showsField(top, 'Language')).toBe(true)
    expect(showsControl(top, 'Sign out')).toBe(false)
  })
})
