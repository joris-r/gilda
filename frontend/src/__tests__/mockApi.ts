import { flushPromises, type DOMWrapper, type VueWrapper } from '@vue/test-utils'
import { vi } from 'vitest'

export interface Reply {
  status: number
  body?: unknown
}

/** A fixed reply, or one computed from the request body (and URL, for its query). */
export type Route = Reply | ((body: unknown, path: string, url: URL) => Reply)

export interface Call {
  method: string
  path: string
  body: unknown
}

/**
 * Stubs fetch with routes keyed by "METHOD /path". Unmocked requests answer 500,
 * so a test sees them fail. Returns the calls made, in order.
 */
export function mockApi(routes: Record<string, Route>): Call[] {
  const calls: Call[] = []
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const request = input instanceof Request ? input : undefined
    const url = new URL(request?.url ?? String(input), 'http://localhost')
    const method = (init?.method ?? request?.method ?? 'GET').toUpperCase()
    const raw = init?.body ?? (request ? await request.text() : undefined)
    const body = raw ? JSON.parse(String(raw)) : undefined
    calls.push({ method, path: url.pathname, body })
    const route = routes[`${method} ${url.pathname}`]
    const reply: Reply =
      route === undefined
        ? { status: 500, body: { error: `not mocked: ${method} ${url.pathname}` } }
        : typeof route === 'function'
          ? route(body, url.pathname, url)
          : route
    return new Response(reply.body === undefined ? null : JSON.stringify(reply.body), {
      status: reply.status,
      headers: { 'Content-Type': 'application/json' },
    })
  })
  vi.stubGlobal('fetch', fetchMock)
  return calls
}

export const signedOut: Route = { status: 401, body: { error: 'Not signed in' } }

type Wrapper = VueWrapper | DOMWrapper<Element>

/** The input or select labelled `label`, by nesting or by `for`. */
export function field(wrapper: Wrapper, label: string): DOMWrapper<Element> {
  const element = wrapper.findAll('label').find((l) => l.text().trim().startsWith(label))
  if (element === undefined) throw new Error(`No field labelled "${label}"`)
  const id = element.attributes('for')
  return id ? wrapper.find(`#${id}`) : element.find('input, select')
}

export async function fill(wrapper: Wrapper, label: string, value: string) {
  await field(wrapper, label).setValue(value)
}

/** The button or link whose text is `text`. */
export function control(wrapper: Wrapper, text: string): DOMWrapper<Element> {
  const element = wrapper.findAll('button, a').find((e) => e.text().trim() === text)
  if (element === undefined) throw new Error(`No button or link "${text}"`)
  return element
}

export function hasControl(wrapper: Wrapper, text: string): boolean {
  return wrapper.findAll('button, a').some((e) => e.text().trim() === text)
}

/** Clicks a button or link; a submit button submits its form. */
export async function press(wrapper: Wrapper, text: string) {
  const element = control(wrapper, text)
  const form = element.element.closest('form')
  const type = element.attributes('type') ?? 'submit'
  if (form && element.element.tagName === 'BUTTON' && type === 'submit') {
    form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))
  } else {
    await element.trigger('click')
  }
  await flushPromises()
}

/** The list item mentioning `text`. */
export function item(wrapper: Wrapper, text: string): DOMWrapper<Element> {
  const element = wrapper.findAll('li').find((li) => li.text().includes(text))
  if (element === undefined) throw new Error(`No list item mentioning "${text}"`)
  return element
}
