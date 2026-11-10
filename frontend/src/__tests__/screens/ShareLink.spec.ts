import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mountApp, pageText } from '../mountApp'
import {
  dialog,
  dialogs,
  hasControl,
  header,
  mockApi,
  press,
  showsControl,
  showsField,
  signedOut,
  type Route,
} from '../mockApi'
import { garden, member, signedInAsAlice } from './fixtures'
import { day, open, planningApi, slotItem, type Occurrence } from './planningFake'

const settingsPath = `/association/${garden.slug}/settings`
const base = `/api/associations/${garden.id}`

function isoDate(d: Date) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

/** Thursday and Saturday 10–13 in the ten weeks from Monday 19 October 2026, but on 14 November. */
function occurrences(): Occurrence[] {
  const list: Occurrence[] = []
  for (let i = 0; i < 70; i++) {
    const d = new Date(2026, 9, 19 + i)
    if ((d.getDay() === 4 || d.getDay() === 6) && isoDate(d) !== '2026-11-14')
      list.push({ date: isoDate(d), start: '10:00', end: '13:00' })
  }
  return list
}

function mount(
  at: string,
  options: {
    role?: 'manager' | 'volunteer'
    shareLink?: string | null
    session?: Route
  } = {},
) {
  const role = options.role ?? 'manager'
  const api = planningApi({
    me: 'u-alice',
    role,
    members: [member('u-alice', 'Alice', role), member('u-chloe', 'Chloé', 'volunteer')],
    occurrences: occurrences(),
    registrations: [
      {
        id: 'r-chloe',
        user_id: 'u-chloe',
        display_name: 'Chloé',
        status: 'confirmed',
        date: '2026-10-29',
        start: '10:00',
        end: '13:00',
      },
      {
        id: 'r-alice',
        user_id: 'u-alice',
        display_name: 'Alice',
        status: 'proposed',
        date: '2026-10-31',
        start: '10:00',
        end: '13:00',
      },
    ],
    closures: [
      { id: 'c-fete', first: '2026-11-14', last: '2026-11-14', label: 'Fête du quartier' },
    ],
    slots: [
      { id: 's-thu', weekday: 'thursday', start: '10:00', end: '13:00' },
      { id: 's-sat', weekday: 'saturday', start: '10:00', end: '13:00' },
    ],
    planningPeriod: { first: '2026-11-02', last: '2026-11-25' },
    shareLink: options.shareLink ?? null,
  })
  const unknown = { status: 404, body: { error: 'Unknown share link' } }
  const calls = mockApi({
    'GET /api/session': options.session ?? signedInAsAlice,
    'GET /api/shared/unknown': unknown,
    'GET /api/shared/unknown/schedule': unknown,
    ...api.routes,
  })
  return { calls, api, mounting: mountApp(at) }
}

/** The text of the Share link section, up to the next section. */
function shareSection(text: string) {
  const start = text.indexOf('Share link')
  const end = text.indexOf("Members' preferences", start)
  return text.slice(start, end < 0 ? undefined : end)
}

beforeEach(() => {
  localStorage.clear()
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(new Date(2026, 9, 28, 10, 0))
})

afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('Schedule settings: Share link', () => {
  // /planning/ui/schedule-settings/share-link
  it('a manager sees the link', async () => {
    const { mounting } = mount(settingsPath, { shareLink: 'tok-1' })
    const section = shareSection(pageText(await mounting))

    expect(section).toContain('/shared/tok-1')
  })

  // /planning/ui/schedule-settings/share-link
  it('shows "None" without a link', async () => {
    const { mounting } = mount(settingsPath)
    const section = shareSection(pageText(await mounting))

    expect(section).toContain('None')
    expect(section).not.toContain('/shared/')
  })

  // /planning/ui/schedule-settings/share-link
  it('in French, "Lien de partage"', async () => {
    localStorage.setItem('gilda.locale', 'fr')
    const { mounting } = mount(settingsPath)

    expect(pageText(await mounting)).toContain('Lien de partage')
  })

  // /planning/ui/schedule-settings/share-link
  it('is not shown to a volunteer, who does not load it', async () => {
    const { calls, mounting } = mount(settingsPath, { role: 'volunteer' })
    const wrapper = await mounting

    expect(pageText(wrapper)).not.toContain('Share link')
    expect(hasControl(wrapper, 'Create a share link')).toBe(false)
    expect(calls.some((c) => c.path === `${base}/share-link`)).toBe(false)
  })

  // /planning/ui/schedule-settings/create-link
  it('"Create a share link" creates it with POST and shows it', async () => {
    const { calls, mounting } = mount(settingsPath)
    const wrapper = await mounting

    await press(wrapper, 'Create a share link')

    expect(calls).toContainEqual({ method: 'POST', path: `${base}/share-link`, body: undefined })
    expect(dialogs(wrapper)).toHaveLength(0)
    expect(shareSection(pageText(wrapper))).toContain('/shared/share-new-')
  })

  // /planning/ui/schedule-settings/create-link
  it('with a link, "Create a share link" first asks "Replace the share link?"', async () => {
    const { calls, mounting } = mount(settingsPath, { shareLink: 'tok-1' })
    const wrapper = await mounting

    await press(wrapper, 'Create a share link')

    expect(dialog(wrapper).text()).toContain(
      'Replace the share link? The current link no longer shows the Schedule.',
    )
    expect(calls.some((c) => c.method === 'POST')).toBe(false)
  })

  // /planning/ui/schedule-settings/create-link
  it('Replace replaces the link with POST', async () => {
    const { calls, mounting } = mount(settingsPath, { shareLink: 'tok-1' })
    const wrapper = await mounting

    await press(wrapper, 'Create a share link')
    await press(dialog(wrapper), 'Replace')

    expect(calls).toContainEqual({ method: 'POST', path: `${base}/share-link`, body: undefined })
    expect(dialogs(wrapper)).toHaveLength(0)
    const section = shareSection(pageText(wrapper))
    expect(section).toContain('/shared/share-new-')
    expect(section).not.toContain('/shared/tok-1')
  })

  // /ui/forms/close
  it('Cancel keeps the link', async () => {
    const { calls, mounting } = mount(settingsPath, { shareLink: 'tok-1' })
    const wrapper = await mounting

    await press(wrapper, 'Create a share link')
    await press(dialog(wrapper), 'Cancel')

    expect(calls.some((c) => c.method === 'POST')).toBe(false)
    expect(shareSection(pageText(wrapper))).toContain('/shared/tok-1')
  })

  // /planning/ui/schedule-settings/copy
  it('"Copy" copies the link and shows "Link copied."', async () => {
    const writeText = vi.fn(async () => {})
    vi.stubGlobal('navigator', { ...navigator, clipboard: { writeText } })
    const { mounting } = mount(settingsPath, { shareLink: 'tok-1' })
    const wrapper = await mounting

    await press(wrapper, 'Copy')

    expect(writeText).toHaveBeenCalledWith(`${window.location.origin}/shared/tok-1`)
    expect(pageText(wrapper)).toContain('Link copied.')
  })

  // /planning/ui/schedule-settings/share-link
  it('offers "Copy" and its delete icon only with a link', async () => {
    const { mounting } = mount(settingsPath)
    const wrapper = await mounting

    expect(hasControl(wrapper, 'Copy')).toBe(false)
    expect(hasControl(wrapper, 'Revoke the share link')).toBe(false)
  })

  // /planning/ui/schedule-settings/revoke-link
  it('its delete icon asks "Revoke the share link?"', async () => {
    const { calls, mounting } = mount(settingsPath, { shareLink: 'tok-1' })
    const wrapper = await mounting

    await press(wrapper, 'Revoke the share link')

    expect(dialog(wrapper).text()).toContain(
      'Revoke the share link? It no longer shows the Schedule.',
    )
    expect(calls.some((c) => c.method === 'DELETE')).toBe(false)
  })

  // /planning/ui/schedule-settings/revoke-link
  it('Revoke revokes the link with DELETE', async () => {
    const { calls, mounting } = mount(settingsPath, { shareLink: 'tok-1' })
    const wrapper = await mounting

    await press(wrapper, 'Revoke the share link')
    await press(dialog(wrapper), 'Revoke')

    expect(calls).toContainEqual({ method: 'DELETE', path: `${base}/share-link`, body: undefined })
    expect(dialogs(wrapper)).toHaveLength(0)
    const section = shareSection(pageText(wrapper))
    expect(section).toContain('None')
    expect(section).not.toContain('/shared/tok-1')
  })
})

describe('Shared schedule', () => {
  const sharedPath = '/shared/tok-1'

  // /planning/ui/shared-schedule/shown
  it('shows the Schedule signed out', async () => {
    const { mounting } = mount(sharedPath, { shareLink: 'tok-1', session: signedOut })
    const wrapper = await mounting

    expect(wrapper.vm.$route.path).toBe(sharedPath)
    expect(slotItem(wrapper, 'Thu 29 Oct', '10–13').text()).toContain('Chloé')
    expect(slotItem(wrapper, 'Sat 31 Oct', '10–13').text()).toMatch(/Alice\s*\?/)
    expect(day(wrapper, 'Sat 14 Nov').text()).toContain('Fête du quartier')
  })

  // /planning/ui/shared-schedule/shown /planning/ui/schedule/weeks
  it('opens on the default weeks, read with the token', async () => {
    const { api, calls, mounting } = mount(sharedPath, { shareLink: 'tok-1', session: signedOut })
    const text = pageText(await mounting)

    expect(api.scheduleRequests).toEqual([{ from: null, to: null }])
    expect(calls.some((c) => c.path.startsWith(base))).toBe(false)
    for (const week of [43, 44, 45, 46, 47, 48]) expect(text).toContain(`Week ${week}`)
    expect(text).not.toContain('Week 42')
  })

  // /planning/ui/shared-schedule/shown /planning/ui/schedule/more
  it('"More weeks" adds four more', async () => {
    const { api, mounting } = mount(sharedPath, { shareLink: 'tok-1', session: signedOut })
    const wrapper = await mounting

    await press(wrapper, 'More weeks')

    // The default range runs to Sun 6 Dec, the week after the planning period's end.
    expect(api.scheduleRequests.some((r) => r.from === '2026-12-07' && r.to === '2027-01-03')).toBe(
      true,
    )
    expect(pageText(wrapper)).toContain('Week 53')
  })

  // /planning/ui/shared-schedule/shown /planning/ui/schedule/today /planning/ui/schedule/period-lines
  it('shows the today and planning period lines', async () => {
    const { mounting } = mount(sharedPath, { shareLink: 'tok-1', session: signedOut })
    const text = pageText(await mounting)

    expect(text).toContain('Today · Wednesday 28 October 2026')
    expect(text).toContain('Planning start · Monday 2 November 2026')
    expect(text).toContain('Planning end · Wednesday 25 November 2026')
  })

  // /planning/ui/shared-schedule/shown
  it('has no links to the other screens', async () => {
    const { mounting } = mount(sharedPath, { shareLink: 'tok-1', session: signedOut })
    const wrapper = await mounting

    expect(hasControl(wrapper, 'My availability')).toBe(false)
    expect(hasControl(wrapper, 'Members')).toBe(false)
    expect(hasControl(wrapper, 'Schedule settings')).toBe(false)
  })

  // /planning/ui/shared-schedule/shown
  it('clicking an occurrence opens no menu', async () => {
    const { calls, mounting } = mount(sharedPath, { shareLink: 'tok-1', session: signedOut })
    const wrapper = await mounting

    await open(slotItem(wrapper, 'Thu 19 Nov', '10–13'))

    expect(wrapper.find('[role="dialog"]').exists()).toBe(false)
    expect(hasControl(wrapper, 'Sign up')).toBe(false)
    expect(calls.some((c) => c.method !== 'GET')).toBe(false)
  })

  // /core/ui/header/shared
  it.each([
    ['signed out', signedOut],
    ['signed in', signedInAsAlice],
  ])(
    '%s, the header shows the association name, leading nowhere, and the language selector alone',
    async (_, session) => {
      const { mounting } = mount(sharedPath, { shareLink: 'tok-1', session })
      const top = header(await mounting)

      expect(top.text()).toContain(garden.name)
      expect(hasControl(top, garden.name)).toBe(false)
      expect(showsField(top, 'Language')).toBe(true)
      expect(top.text()).not.toContain('Alice')
      expect(showsControl(top, 'Sign out')).toBe(false)
    },
  )

  // /planning/ui/shared-schedule/shown
  it('signed in, shows the Schedule too', async () => {
    const { mounting } = mount(sharedPath, { shareLink: 'tok-1' })

    expect(slotItem(await mounting, 'Thu 29 Oct', '10–13').text()).toContain('Chloé')
  })

  // /planning/ui/shared-schedule/invalid
  it('an unknown link shows "This link is no longer valid."', async () => {
    const { mounting } = mount('/shared/unknown', { session: signedOut })
    const text = pageText(await mounting)

    expect(text).toContain('This link is no longer valid.')
    expect(text).not.toContain('Week 44')
  })

  // /planning/ui/shared-schedule/invalid
  it('a revoked link shows "This link is no longer valid."', async () => {
    mockApi({
      'GET /api/session': signedOut,
      'GET /api/shared/tok-1': { status: 404, body: { error: 'Unknown share link' } },
      'GET /api/shared/tok-1/schedule': { status: 404, body: { error: 'Unknown share link' } },
    })

    const text = pageText(await mountApp(sharedPath))

    expect(text).toContain('This link is no longer valid.')
  })
})
