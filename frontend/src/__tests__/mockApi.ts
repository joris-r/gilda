import { DOMWrapper, flushPromises, type VueWrapper } from '@vue/test-utils'
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

const callHeaders = new WeakMap<Call, Headers>()

/** The headers `call` was sent with. */
export function headersOf(call: Call): Headers {
  return callHeaders.get(call) ?? new Headers()
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
    const call = { method, path: url.pathname, body }
    callHeaders.set(call, new Headers(init?.headers ?? request?.headers))
    calls.push(call)
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

/** Whether `element` is named `name`: by its text, a leading "+" aside, or else by its aria-label or title. */
function named(element: DOMWrapper<Element>, name: string): boolean {
  return (
    element
      .text()
      .trim()
      .replace(/^\+\s*/, '') === name ||
    element.attributes('aria-label') === name ||
    element.attributes('title') === name
  )
}

/** The button or link named `text`. */
export function control(wrapper: Wrapper, text: string): DOMWrapper<Element> {
  const element = wrapper.findAll('button, a').find((e) => named(e, text))
  if (element === undefined) throw new Error(`No button or link "${text}"`)
  return element
}

export function hasControl(wrapper: Wrapper, text: string): boolean {
  return wrapper.findAll('button, a').some((e) => named(e, text))
}

/** Whether a button or link named `text` is present and visible. */
export function showsControl(wrapper: Wrapper, text: string): boolean {
  return wrapper.findAll('button, a').some((e) => named(e, text) && e.isVisible())
}

/** Whether a field labelled `label` is present and visible. */
export function showsField(wrapper: Wrapper, label: string): boolean {
  try {
    return field(wrapper, label).isVisible()
  } catch {
    return false
  }
}

/** The page header. */
export function header(wrapper: VueWrapper): DOMWrapper<Element> {
  return wrapper.find('header')
}

/** Opens the menu of the header's button showing `displayName`. */
export async function openUserMenu(wrapper: VueWrapper, displayName: string) {
  const button = header(wrapper)
    .findAll('button')
    .find((b) => b.text().includes(displayName))
  if (button === undefined) throw new Error(`No header button "${displayName}"`)
  await button.trigger('click')
  await flushPromises()
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

const DIALOG = '[role="dialog"], [role="alertdialog"], dialog[open]'

/** The open dialogs, inside `wrapper` or teleported to the document, innermost last. */
export function dialogs(wrapper: VueWrapper): DOMWrapper<Element>[] {
  const elements = new Set<Element>([
    ...wrapper.findAll(DIALOG).map((d) => d.element),
    ...document.body.querySelectorAll(DIALOG),
  ])
  return [...elements].map((e) => new DOMWrapper(e)).filter((d) => d.isVisible())
}

/** The title of `dialog`: its aria-label, its aria-labelledby element, or its first heading. */
export function titleOf(dialog: DOMWrapper<Element>): string {
  const label = dialog.attributes('aria-label')
  if (label) return label.trim()
  const by = dialog.attributes('aria-labelledby')
  const labelling = by ? dialog.element.querySelector(`[id="${by}"]`) : null
  if (labelling) return labelling.textContent?.trim() ?? ''
  return dialog.find('h1, h2, h3').exists() ? dialog.find('h1, h2, h3').text().trim() : ''
}

/** The innermost open dialog, failing when none is open. */
export function dialog(wrapper: VueWrapper): DOMWrapper<Element> {
  const open = dialogs(wrapper)
  if (open.length === 0) throw new Error('No open dialog')
  return open[open.length - 1]!
}

/** Presses Escape in `target`, then on the document if it is still open. */
export async function pressEscape(wrapper: VueWrapper, target: DOMWrapper<Element>) {
  const escape = () => new KeyboardEvent('keydown', { key: 'Escape', bubbles: true })
  target.element.dispatchEvent(escape())
  await flushPromises()
  if (dialogs(wrapper).some((d) => d.element === target.element)) {
    document.dispatchEvent(escape())
    await flushPromises()
  }
}
