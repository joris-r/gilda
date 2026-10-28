import { flushPromises } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mountApp, pageText } from '../../__tests__/mountApp'

function answerHealth(status: number, body: object) {
  const fetchMock = vi.fn().mockResolvedValue(
    new Response(JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json' },
    }),
  )
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

beforeEach(() => {
  localStorage.clear()
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('Status page', () => {
  it('calls GET /api/health', async () => {
    const fetchMock = answerHealth(200, { api: 'ok', database: 'ok' })

    await mountApp('/')

    expect(fetchMock).toHaveBeenCalled()
    const [url, init] = fetchMock.mock.calls[0] as [RequestInfo | URL, RequestInit | undefined]
    expect(String(url)).toMatch(/(^|\/\/[^/]+)\/api\/health$/)
    expect(init?.method ?? 'GET').toBe('GET')
  })

  it('shows the API and the database reachable', async () => {
    answerHealth(200, { api: 'ok', database: 'ok' })

    const text = pageText(await mountApp('/'))

    expect(text).toContain('Gilda status')
    expect(text).toContain('API: reachable')
    expect(text).toContain('Database: reachable')
  })

  it('shows the database unreachable', async () => {
    answerHealth(503, { api: 'ok', database: 'unreachable' })

    const text = pageText(await mountApp('/'))

    expect(text).toContain('API: reachable')
    expect(text).toContain('Database: unreachable')
  })

  it('shows the API unreachable when it does not answer', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    const text = pageText(await mountApp('/'))

    expect(text).toContain('API: unreachable')
    expect(text).toContain('Database: unknown')
  })
})

describe('Language selector', () => {
  it('shows the interface in English by default', async () => {
    answerHealth(200, { api: 'ok', database: 'ok' })

    const text = pageText(await mountApp('/'))

    expect(text).toContain('Gilda status')
  })

  it('switches the status page to French', async () => {
    answerHealth(200, { api: 'ok', database: 'ok' })
    const wrapper = await mountApp('/')

    await wrapper.find('select').setValue('fr')
    await flushPromises()

    const text = pageText(wrapper)
    expect(text).toContain('État de Gilda')
    expect(text).toContain('API : accessible')
    expect(text).toContain('Base de données : accessible')
  })

  it('switches back to English', async () => {
    answerHealth(200, { api: 'ok', database: 'ok' })
    const wrapper = await mountApp('/')

    await wrapper.find('select').setValue('fr')
    await wrapper.find('select').setValue('en')
    await flushPromises()

    expect(pageText(wrapper)).toContain('Gilda status')
  })
})
