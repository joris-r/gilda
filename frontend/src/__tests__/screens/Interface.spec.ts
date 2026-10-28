import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mountApp, pageText } from '../mountApp'
import { field, item, mockApi } from '../mockApi'
import { garden, repairCafe, signedInAsAlice } from './fixtures'

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
        { ...garden, role: 'manager' },
        { ...repairCafe, role: 'volunteer' },
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

    await field(first, 'Langue').setValue('en')
    first.unmount()
    const second = await mountApp('/')

    expect(pageText(second)).toContain('My associations')
  })
})
