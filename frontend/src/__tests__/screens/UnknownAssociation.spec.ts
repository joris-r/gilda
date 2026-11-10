import { flushPromises } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mountApp, pageText } from '../mountApp'
import { mockApi } from '../mockApi'
import { garden, signedInAsAlice } from './fixtures'

beforeEach(() => {
  localStorage.clear()
})

afterEach(() => {
  vi.unstubAllGlobals()
})

const MESSAGE = 'This association does not exist or you are not a member.'
const unknown = 'plus-par-ici'

describe('A screen of an association whose slug is unknown', () => {
  describe.each([
    ['Schedule', `/association/${unknown}`],
    ['Members', `/association/${unknown}/members`],
    ['Schedule settings', `/association/${unknown}/settings`],
    ['My availability', `/association/${unknown}/availability`],
  ])('%s', (_screen, path) => {
    function mountUnknown() {
      mockApi({
        'GET /api/session': signedInAsAlice,
        'GET /api/associations': { status: 200, body: [] },
        [`GET /api/associations/by-slug/${unknown}`]: {
          status: 404,
          body: { error: 'Not found' },
        },
      })
      return mountApp(path)
    }

    // /core/ui/unknown-association/shown
    it('says so', async () => {
      const wrapper = await mountUnknown()

      expect(pageText(wrapper)).toContain(MESSAGE)
    })

    // /core/ui/unknown-association/shown
    it('has a way to My associations', async () => {
      const wrapper = await mountUnknown()
      const way = wrapper
        .findAll('main a, main button')
        .find((element) => element.text().includes('My associations'))
      if (way === undefined) throw new Error('No way to My associations on the screen')

      await way.trigger('click')
      await flushPromises()

      expect(wrapper.vm.$route.path).toBe('/')
    })
  })

  // /core/ui/unknown-association/shown
  it('does not show for an association the user is a member of', async () => {
    mockApi({
      'GET /api/session': signedInAsAlice,
      [`GET /api/associations/by-slug/${garden.slug}`]: {
        status: 200,
        body: { ...garden, role: 'volunteer', members: [] },
      },
    })
    const wrapper = await mountApp(`/association/${garden.slug}/members`)

    expect(pageText(wrapper)).not.toContain(MESSAGE)
  })
})
