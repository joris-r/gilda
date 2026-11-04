import type { DOMWrapper } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mountApp, pageText } from '../mountApp'
import { control, hasControl, header, mockApi, press } from '../mockApi'
import { garden, member, signedInAsAlice } from './fixtures'
import {
  day,
  hasDay,
  isAbsent,
  menu,
  open,
  planningApi,
  preferenceOf,
  slotItem,
  type Closure,
  type MemberAbsence,
  type Note,
  type Occurrence,
  type PlanningPeriod,
  type Preference,
  type Registration,
  type RegistrationCount,
} from './planningFake'

const alice = member('u-alice', 'Alice', 'volunteer')
const bruno = member('u-bruno', 'Bruno', 'volunteer')
const chloe = member('u-chloe', 'Chloé', 'volunteer')
const path = `/associations/${garden.slug}`
const registrationsPath = `/api/associations/${garden.id}/registrations`

function isoDate(d: Date) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

/** Thursday and Saturday 10–13 in the ten weeks from Monday 19 October 2026, but on a closure. */
function occurrences(closed: string[]): Occurrence[] {
  const list: Occurrence[] = []
  for (let i = 0; i < 70; i++) {
    const d = new Date(2026, 9, 19 + i)
    if ((d.getDay() === 4 || d.getDay() === 6) && !closed.includes(isoDate(d)))
      list.push({ date: isoDate(d), start: '10:00', end: '13:00' })
  }
  return list
}

const closure: Closure = {
  id: 'c-fete',
  first: '2026-11-14',
  last: '2026-11-14',
  label: 'Fête du quartier',
}

function registration(
  id: string,
  who: ReturnType<typeof member>,
  status: Registration['status'],
  date: string,
  start = '10:00',
  end = '13:00',
): Registration {
  return { id, user_id: who.user_id, display_name: who.display_name, status, date, start, end }
}

const registrations = [
  registration('r-past', bruno, 'confirmed', '2026-10-22'),
  registration('r-chloe', chloe, 'confirmed', '2026-10-29'),
  registration('r-proposed', alice, 'proposed', '2026-10-31'),
  registration('r-mine', alice, 'confirmed', '2026-11-05'),
  registration('r-cancelled', bruno, 'cancelled', '2026-11-07'),
  registration('r-obsolete', alice, 'proposed', '2026-11-12', '10:00', '12:00'),
]

function mountSchedule(
  role: 'manager' | 'volunteer' = 'volunteer',
  overrides: {
    occurrences?: Occurrence[]
    registrations?: Registration[]
    planningPeriod?: PlanningPeriod
    preferences?: Preference[]
    registrationCounts?: RegistrationCount[]
    memberAbsences?: MemberAbsence[]
    notes?: Note[]
    members?: ReturnType<typeof member>[]
    scheduleRange?: { from: string; to: string }
  } = {},
  at = path,
) {
  const api = planningApi({
    me: alice.user_id,
    role,
    members: (overrides.members ?? [alice, bruno, chloe]).map((m) =>
      m.user_id === alice.user_id ? { ...m, role } : m,
    ),
    occurrences: overrides.occurrences ?? occurrences(['2026-11-14']),
    registrations: overrides.registrations ?? registrations.map((r) => ({ ...r })),
    closures: [closure],
    slots: [
      { id: 's-thu', weekday: 'thursday', start: '10:00', end: '13:00' },
      { id: 's-sat', weekday: 'saturday', start: '10:00', end: '13:00' },
    ],
    planningPeriod: overrides.planningPeriod ?? null,
    preferences: overrides.preferences,
    registrationCounts: overrides.registrationCounts,
    memberAbsences: overrides.memberAbsences,
    notes: overrides.notes,
    scheduleRange: overrides.scheduleRange,
  })
  const calls = mockApi({ 'GET /api/session': signedInAsAlice, ...api.routes })
  return { calls, api, mounting: mountApp(at) }
}

/** The texts of the elements that have no child element. */
function leafTexts(wrapper: { findAll(selector: string): { element: Element }[] }) {
  return wrapper
    .findAll('*')
    .filter((w) => w.element.children.length === 0)
    .map((w) => (w.element.textContent ?? '').trim())
}

beforeEach(() => {
  localStorage.clear()
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(new Date(2026, 9, 28, 10, 0))
})

afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

describe('Schedule', () => {
  it('the header shows the association name alone', async () => {
    const { mounting } = mountSchedule()
    const text = header(await mounting).text()

    expect(text).toContain(garden.name)
    expect(text).not.toContain('Schedule')
    expect(text).not.toContain('Members')
  })

  it('"My availability", "Members" and "Schedule settings" lead to those screens', async () => {
    const { mounting } = mountSchedule()
    const wrapper = await mounting

    expect(control(wrapper, 'My availability').attributes('href')).toBe(`${path}/availability`)
    expect(control(wrapper, 'Members').attributes('href')).toBe(`${path}/members`)
    expect(control(wrapper, 'Schedule settings').attributes('href')).toBe(`${path}/settings`)
  })

  it('week headings show only the week number', async () => {
    const { mounting } = mountSchedule()
    const text = pageText(await mounting)

    expect(text).toContain('Week 44')
    expect(text).not.toContain('26 Oct – 1 Nov')
  })

  it('no longer opens at /associations/{slug}/schedule', async () => {
    const { mounting } = mountSchedule('volunteer', {}, `${path}/schedule`)
    const text = pageText(await mounting)

    expect(text).not.toContain('Week 44')
  })

  it('opens on the weeks of R32, in one request', async () => {
    const { api, mounting } = mountSchedule()
    const wrapper = await mounting

    expect(api.scheduleRequests).toEqual([{ from: null, to: null }])
    const text = pageText(wrapper)
    for (const week of [43, 44, 45, 46, 47, 48]) expect(text).toContain(`Week ${week}`)
    expect(text).not.toContain('Week 42')
    expect(text).not.toContain('Week 49')
  })

  it('"More weeks", at the end, adds four more', async () => {
    const { api, mounting } = mountSchedule()
    const wrapper = await mounting

    await press(wrapper, 'More weeks')

    expect(api.scheduleRequests.some((r) => r.to === '2026-12-27')).toBe(true)
    const text = pageText(wrapper)
    for (const week of [43, 49, 50, 51, 52]) expect(text).toContain(`Week ${week}`)
    expect(text).not.toContain('Week 53')
    expect(text.indexOf('Week 52')).toBeLessThan(text.indexOf('More weeks'))
  })

  it("a line marked with today's date separates the past weeks from the current week", async () => {
    const { mounting } = mountSchedule()
    const text = pageText(await mounting)

    const line = text.indexOf('Today · Wednesday 28 October 2026')
    expect(line).toBeGreaterThan(text.indexOf('Week 43'))
    expect(line).toBeLessThan(text.indexOf('Week 44'))
  })

  describe('R11', () => {
    it("after midnight in Paris, today is Paris's date", async () => {
      vi.setSystemTime(new Date('2026-10-29T23:30:00Z'))
      const { mounting } = mountSchedule('volunteer', { registrations: [] })
      const wrapper = await mounting

      expect(pageText(wrapper)).toContain('Today · Friday 30 October 2026')
      await open(slotItem(wrapper, 'Thu 29 Oct', '10–13'))
      expect(hasControl(wrapper, 'Sign up')).toBe(false)
    })

    it('before midnight in Paris, today is still that day', async () => {
      vi.setSystemTime(new Date('2026-10-29T22:30:00Z'))
      const { mounting } = mountSchedule('volunteer', { registrations: [] })
      const wrapper = await mounting

      expect(pageText(wrapper)).toContain('Today · Thursday 29 October 2026')
      await open(slotItem(wrapper, 'Thu 29 Oct', '10–13'))
      expect(hasControl(wrapper, 'Sign up')).toBe(true)
    })

    it('in summer time, today follows Paris too', async () => {
      vi.setSystemTime(new Date('2026-07-01T22:30:00Z'))
      const { mounting } = mountSchedule('volunteer', {
        occurrences: [{ date: '2026-07-02', start: '10:00', end: '13:00' }],
        registrations: [],
      })

      expect(pageText(await mounting)).toContain('Today · Thursday 2 July 2026')
    })
  })

  it('each week has one column per weekday on which an occurrence falls', async () => {
    const { mounting } = mountSchedule()
    const wrapper = await mounting

    expect(day(wrapper, 'Thu 22 Oct').exists()).toBe(true)
    expect(day(wrapper, 'Sat 31 Oct').exists()).toBe(true)
    for (const other of ['Mon', 'Tue', 'Wed', 'Fri', 'Sun'])
      expect(hasDay(wrapper, other)).toBe(false)
  })

  it('time runs from the earliest start to the latest end, rounded to whole hours', async () => {
    const { mounting } = mountSchedule('volunteer', {
      occurrences: [
        { date: '2026-10-29', start: '10:30', end: '12:15' },
        { date: '2026-10-31', start: '16:00', end: '16:45' },
      ],
      registrations: [],
    })
    const texts = leafTexts(await mounting)

    expect(texts).toContain('10h')
    expect(texts).toContain('17h')
    expect(texts).not.toContain('9h')
    expect(texts).not.toContain('18h')
  })

  it("an occurrence shows its registration's display name, and no times", async () => {
    const { mounting } = mountSchedule()
    const wrapper = await mounting

    const occurrence = slotItem(wrapper, 'Thu 29 Oct', '10–13')
    expect(occurrence.text()).toContain('Chloé')
    expect(occurrence.text()).not.toMatch(/Chloé\s*\?/)
    expect(occurrence.text()).not.toContain('10–13')
  })

  it('a proposed registration shows "?"', async () => {
    const { mounting } = mountSchedule()

    expect(slotItem(await mounting, 'Sat 31 Oct', '10–13').text()).toMatch(/Alice\s*\?/)
  })

  it('an occurrence without registration is empty', async () => {
    const { mounting } = mountSchedule()

    expect(
      slotItem(await mounting, 'Thu 19 Nov', '10–13')
        .text()
        .trim(),
    ).toBe('')
  })

  it('the menu of an occurrence is titled with its day and times', async () => {
    const { mounting } = mountSchedule()
    const wrapper = await mounting

    await open(slotItem(wrapper, 'Thu 19 Nov', '10–13'))
    expect(menu(wrapper).text()).toContain('Thu 19 Nov · 10–13')
  })

  it('a cancelled registration shows its name struck', async () => {
    const { mounting } = mountSchedule()

    expect(
      slotItem(await mounting, 'Sat 7 Nov', '10–13')
        .find('s')
        .text(),
    ).toBe('Bruno')
  })

  it('an obsolete registration is placed on its day, marked "obsolete"', async () => {
    const { mounting } = mountSchedule()
    const wrapper = await mounting

    const obsolete = slotItem(wrapper, 'Thu 12 Nov', '10–12')
    expect(obsolete.text()).toContain('Alice')
    expect(obsolete.text()).toContain('obsolete')
    expect(slotItem(wrapper, 'Thu 12 Nov', '10–13').text()).not.toContain('obsolete')
  })

  it('a day covered by a closure shows "Closed" and its label', async () => {
    const { mounting } = mountSchedule()
    const text = day(await mounting, 'Sat 14 Nov').text()

    expect(text).toContain('Closed')
    expect(text).toContain('Fête du quartier')
  })

  describe('planning period', () => {
    const period = { first: '2026-11-04', last: '2026-11-18' }

    it('a line marked with the first date sits just before the week that holds it', async () => {
      const { mounting } = mountSchedule('volunteer', { planningPeriod: period })
      const text = pageText(await mounting)

      const line = text.indexOf('Planning start · Wednesday 4 November 2026')
      expect(line).toBeGreaterThan(text.indexOf('Week 44'))
      expect(line).toBeLessThan(text.indexOf('Week 45'))
    })

    it('a line marked with the last date sits just after the week that holds it', async () => {
      const { mounting } = mountSchedule('volunteer', { planningPeriod: period })
      const text = pageText(await mounting)

      const line = text.indexOf('Planning end · Wednesday 18 November 2026')
      expect(line).toBeGreaterThan(text.indexOf('Week 47'))
      expect(line).toBeLessThan(text.indexOf('Week 48'))
    })

    it('the today line comes first when the first line falls at the same place', async () => {
      const { mounting } = mountSchedule('volunteer', {
        planningPeriod: { first: '2026-10-26', last: '2026-11-18' },
      })
      const text = pageText(await mounting)

      const today = text.indexOf('Today · Wednesday 28 October 2026')
      const first = text.indexOf('Planning start · Monday 26 October 2026')
      expect(today).toBeGreaterThan(text.indexOf('Week 43'))
      expect(first).toBeGreaterThan(today)
      expect(first).toBeLessThan(text.indexOf('Week 44'))
    })

    it('R32: the schedule opens on all the weeks the range of the reply covers', async () => {
      const { api, mounting } = mountSchedule('volunteer', {
        planningPeriod: { first: '2026-11-04', last: '2026-11-25' },
        scheduleRange: { from: '2026-10-19', to: '2026-12-06' },
      })
      const wrapper = await mounting
      const text = pageText(wrapper)

      expect(api.scheduleRequests).toEqual([{ from: null, to: null }])
      for (const week of [43, 48, 49]) expect(text).toContain(`Week ${week}`)
      expect(text).not.toContain('Week 42')
      expect(text).not.toContain('Week 50')

      await press(wrapper, 'More weeks')
      expect(api.scheduleRequests).toContainEqual({ from: '2026-12-07', to: '2027-01-03' })
    })

    it('shows no line without a period', async () => {
      const { mounting } = mountSchedule()
      const text = pageText(await mounting)

      expect(text).not.toContain('Planning start')
      expect(text).not.toContain('Planning end')
    })

    it('an occurrence after the last date keeps its menu', async () => {
      const { calls, mounting } = mountSchedule('volunteer', { planningPeriod: period })
      const wrapper = await mounting

      await open(slotItem(wrapper, 'Thu 19 Nov', '10–13'))
      await press(wrapper, 'Sign up')

      expect(calls).toContainEqual({
        method: 'POST',
        path: registrationsPath,
        body: { user_id: 'u-alice', date: '2026-11-19', start: '10:00', end: '13:00' },
      })
    })
  })

  describe('menu', () => {
    it('a free occurrence offers "Sign up", which registers me', async () => {
      const { calls, mounting } = mountSchedule()
      const wrapper = await mounting

      await open(slotItem(wrapper, 'Thu 19 Nov', '10–13'))
      await press(wrapper, 'Sign up')

      expect(calls).toContainEqual({
        method: 'POST',
        path: registrationsPath,
        body: { user_id: 'u-alice', date: '2026-11-19', start: '10:00', end: '13:00' },
      })
      expect(slotItem(wrapper, 'Thu 19 Nov', '10–13').text()).toContain('Alice')
    })

    it('an occurrence with a cancelled registration offers "Sign up"', async () => {
      const { mounting } = mountSchedule()
      const wrapper = await mounting

      await open(slotItem(wrapper, 'Sat 7 Nov', '10–13'))

      expect(hasControl(wrapper, 'Sign up')).toBe(true)
    })

    it('opens on no occurrence before today', async () => {
      const { mounting } = mountSchedule('manager')
      const wrapper = await mounting

      await open(slotItem(wrapper, 'Thu 22 Oct', '10–13'))

      expect(hasControl(wrapper, 'Sign up')).toBe(false)
      expect(hasControl(wrapper, 'Cancel registration…')).toBe(false)
    })

    it("offers a volunteer nothing on another member's registration", async () => {
      const { mounting } = mountSchedule()
      const wrapper = await mounting

      await open(slotItem(wrapper, 'Thu 29 Oct', '10–13'))

      expect(hasControl(wrapper, 'Sign up')).toBe(false)
      expect(hasControl(wrapper, 'Cancel registration…')).toBe(false)
    })

    it('my proposed registration offers "Confirm", which confirms it', async () => {
      const { calls, mounting } = mountSchedule()
      const wrapper = await mounting

      await open(slotItem(wrapper, 'Sat 31 Oct', '10–13'))
      await press(wrapper, 'Confirm')

      expect(calls).toContainEqual({
        method: 'PATCH',
        path: `${registrationsPath}/r-proposed`,
        body: { status: 'confirmed' },
      })
      expect(slotItem(wrapper, 'Sat 31 Oct', '10–13').text()).not.toMatch(/Alice\s*\?/)
    })

    it('my confirmed registration offers no "Confirm"', async () => {
      const { mounting } = mountSchedule()
      const wrapper = await mounting

      await open(slotItem(wrapper, 'Thu 5 Nov', '10–13'))

      expect(hasControl(wrapper, 'Confirm')).toBe(false)
      expect(hasControl(wrapper, 'Cancel registration…')).toBe(true)
    })

    it('"Cancel registration…" asks before cancelling', async () => {
      const { calls, mounting } = mountSchedule()
      const wrapper = await mounting

      await open(slotItem(wrapper, 'Thu 5 Nov', '10–13'))
      await press(wrapper, 'Cancel registration…')

      expect(pageText(wrapper)).toContain('Cancel this registration?')
      expect(calls.some((c) => c.method === 'PATCH')).toBe(false)
    })

    it('"Yes, cancel" cancels the registration, whose name shows struck', async () => {
      const { calls, mounting } = mountSchedule()
      const wrapper = await mounting

      await open(slotItem(wrapper, 'Thu 5 Nov', '10–13'))
      await press(wrapper, 'Cancel registration…')
      await press(wrapper, 'Yes, cancel')

      expect(calls).toContainEqual({
        method: 'PATCH',
        path: `${registrationsPath}/r-mine`,
        body: { status: 'cancelled' },
      })
      expect(slotItem(wrapper, 'Thu 5 Nov', '10–13').find('s').text()).toBe('Alice')
    })

    it('"Keep it" leaves the registration', async () => {
      const { calls, mounting } = mountSchedule()
      const wrapper = await mounting

      await open(slotItem(wrapper, 'Thu 5 Nov', '10–13'))
      await press(wrapper, 'Cancel registration…')
      await press(wrapper, 'Keep it')

      expect(calls.some((c) => c.method === 'PATCH')).toBe(false)
      expect(slotItem(wrapper, 'Thu 5 Nov', '10–13').find('s').exists()).toBe(false)
    })

    it('my obsolete registration can be cancelled, not confirmed', async () => {
      const { mounting } = mountSchedule()
      const wrapper = await mounting

      await open(slotItem(wrapper, 'Thu 12 Nov', '10–12'))

      expect(hasControl(wrapper, 'Confirm')).toBe(false)
      expect(hasControl(wrapper, 'Cancel registration…')).toBe(true)
    })
  })

  describe('menu, for a manager', () => {
    it('a free occurrence lists the members, each proposing it to that member', async () => {
      const { calls, mounting } = mountSchedule('manager')
      const wrapper = await mounting

      await open(slotItem(wrapper, 'Thu 19 Nov', '10–13'))
      expect(hasControl(wrapper, 'Sign up')).toBe(true)
      expect(hasControl(menu(wrapper), 'Chloé')).toBe(true)
      await press(menu(wrapper), 'Bruno')

      expect(calls).toContainEqual({
        method: 'POST',
        path: registrationsPath,
        body: { user_id: 'u-bruno', date: '2026-11-19', start: '10:00', end: '13:00' },
      })
      expect(slotItem(wrapper, 'Thu 19 Nov', '10–13').text()).toMatch(/Bruno\s*\?/)
    })

    it("cancels another member's registration, after asking", async () => {
      const { calls, mounting } = mountSchedule('manager')
      const wrapper = await mounting

      await open(slotItem(wrapper, 'Thu 29 Oct', '10–13'))
      await press(wrapper, 'Cancel registration…')
      await press(wrapper, 'Yes, cancel')

      expect(calls).toContainEqual({
        method: 'PATCH',
        path: `${registrationsPath}/r-chloe`,
        body: { status: 'cancelled' },
      })
      expect(slotItem(wrapper, 'Thu 29 Oct', '10–13').find('s').text()).toBe('Chloé')
    })

    it('another member\'s proposed registration offers "Confirm", which confirms it', async () => {
      const { calls, mounting } = mountSchedule('manager', {
        registrations: [registration('r-bruno', bruno, 'proposed', '2026-11-19')],
      })
      const wrapper = await mounting

      await open(slotItem(wrapper, 'Thu 19 Nov', '10–13'))
      expect(hasControl(wrapper, 'Cancel registration…')).toBe(true)
      await press(wrapper, 'Confirm')

      expect(calls).toContainEqual({
        method: 'PATCH',
        path: `${registrationsPath}/r-bruno`,
        body: { status: 'confirmed' },
      })
      expect(slotItem(wrapper, 'Thu 19 Nov', '10–13').text()).not.toMatch(/Bruno\s*\?/)
    })
  })

  describe('menu, for a manager: preferences and registration counts', () => {
    const preferences: Preference[] = [
      { user_id: 'u-alice', slot_id: 's-thu', value: 'possible' },
      { user_id: 'u-bruno', slot_id: 's-thu', value: 'preferred' },
      { user_id: 'u-bruno', slot_id: 's-sat', value: 'unavailable' },
      { user_id: 'u-chloe', slot_id: 's-sat', value: 'preferred' },
    ]
    const registrationCounts: RegistrationCount[] = [
      { user_id: 'u-alice', count: 1 },
      { user_id: 'u-bruno', count: 0 },
      { user_id: 'u-chloe', count: 2 },
    ]
    const planningPeriod = { first: '2026-11-02', last: '2026-11-25' }

    /** The menu's buttons proposing the occurrence, in order. */
    function memberButtons(wrapper: { findAll(selector: string): DOMWrapper<Element>[] }) {
      return wrapper
        .findAll('button')
        .filter((b) => /^(Alice|Bruno|Chloé)( \(\d+\))?$/.test(b.text().trim()))
    }

    it("each member's name is marked with their preference for the occurrence's slot", async () => {
      const { mounting } = mountSchedule('manager', { preferences })
      const wrapper = await mounting

      await open(slotItem(wrapper, 'Thu 19 Nov', '10–13'))
      expect(preferenceOf(control(menu(wrapper), 'Alice'))).toBe('possible')
      expect(preferenceOf(control(menu(wrapper), 'Bruno'))).toBe('preferred')
      expect(preferenceOf(control(menu(wrapper), 'Chloé'))).toBeNull()
    })

    it('on another slot, the names follow that slot', async () => {
      const { mounting } = mountSchedule('manager', { preferences })
      const wrapper = await mounting

      await open(slotItem(wrapper, 'Sat 21 Nov', '10–13'))
      expect(preferenceOf(control(menu(wrapper), 'Alice'))).toBeNull()
      expect(preferenceOf(control(menu(wrapper), 'Bruno'))).toBe('unavailable')
      expect(preferenceOf(control(menu(wrapper), 'Chloé'))).toBe('preferred')
    })

    it('each name is followed by the registration count, in parentheses', async () => {
      const { mounting } = mountSchedule('manager', {
        preferences,
        registrationCounts,
        planningPeriod,
      })
      const wrapper = await mounting

      await open(slotItem(wrapper, 'Thu 19 Nov', '10–13'))
      expect(hasControl(menu(wrapper), 'Alice (1)')).toBe(true)
      expect(hasControl(menu(wrapper), 'Bruno (0)')).toBe(true)
      expect(hasControl(menu(wrapper), 'Chloé (2)')).toBe(true)
    })

    it('without a planning period, no count is shown', async () => {
      const { mounting } = mountSchedule('manager', { preferences })
      const wrapper = await mounting

      await open(slotItem(wrapper, 'Thu 19 Nov', '10–13'))
      expect(memberButtons(menu(wrapper)).map((b) => b.text().trim())).toEqual([
        'Bruno',
        'Alice',
        'Chloé',
      ])
    })

    it('the actions are unchanged', async () => {
      const { calls, mounting } = mountSchedule('manager', {
        preferences,
        registrationCounts,
        planningPeriod,
      })
      const wrapper = await mounting

      await open(slotItem(wrapper, 'Thu 19 Nov', '10–13'))
      expect(hasControl(wrapper, 'Sign up')).toBe(true)
      await press(menu(wrapper), 'Chloé (2)')

      expect(calls).toContainEqual({
        method: 'POST',
        path: registrationsPath,
        body: { user_id: 'u-chloe', date: '2026-11-19', start: '10:00', end: '13:00' },
      })
    })

    it('a volunteer does not load the registration counts', async () => {
      const { calls, mounting } = mountSchedule('volunteer', { planningPeriod })
      const wrapper = await mounting

      await open(slotItem(wrapper, 'Thu 19 Nov', '10–13'))
      expect(hasControl(wrapper, 'Sign up')).toBe(true)
      expect(calls.some((c) => c.path.endsWith('/registration-counts'))).toBe(false)
    })
  })

  describe('menu, for a manager: absences and notes', () => {
    const brunoAway: MemberAbsence = {
      id: 'ab-bruno',
      user_id: 'u-bruno',
      first: '2026-11-16',
      last: '2026-11-19',
    }

    it('a member with an absence covering the date is marked absent', async () => {
      const { mounting } = mountSchedule('manager', { memberAbsences: [brunoAway] })
      const wrapper = await mounting

      await open(slotItem(wrapper, 'Thu 19 Nov', '10–13'))
      expect(isAbsent(control(menu(wrapper), 'Bruno'))).toBe(true)
      expect(isAbsent(control(menu(wrapper), 'Alice'))).toBe(false)
      expect(isAbsent(control(menu(wrapper), 'Chloé'))).toBe(false)
    })

    it('an absence covers the dates from its first to its last', async () => {
      const { mounting } = mountSchedule('manager', {
        memberAbsences: [
          { id: 'ab-bruno', user_id: 'u-bruno', first: '2026-11-19', last: '2026-11-25' },
          { id: 'ab-chloe', user_id: 'u-chloe', first: '2026-11-10', last: '2026-11-19' },
          { id: 'ab-alice-1', user_id: 'u-alice', first: '2026-11-13', last: '2026-11-18' },
          { id: 'ab-alice-2', user_id: 'u-alice', first: '2026-11-20', last: '2026-11-21' },
        ],
      })
      const wrapper = await mounting

      await open(slotItem(wrapper, 'Thu 19 Nov', '10–13'))
      expect(isAbsent(control(menu(wrapper), 'Bruno'))).toBe(true)
      expect(isAbsent(control(menu(wrapper), 'Chloé'))).toBe(true)
      expect(isAbsent(control(menu(wrapper), 'Alice'))).toBe(false)
    })

    it('an absent member keeps no preference colour, and can still be proposed the occurrence', async () => {
      const { calls, mounting } = mountSchedule('manager', {
        memberAbsences: [brunoAway],
        preferences: [{ user_id: 'u-bruno', slot_id: 's-thu', value: 'preferred' }],
      })
      const wrapper = await mounting

      await open(slotItem(wrapper, 'Thu 19 Nov', '10–13'))
      expect(preferenceOf(control(menu(wrapper), 'Bruno'))).toBeNull()
      await press(menu(wrapper), 'Bruno')

      expect(calls).toContainEqual({
        method: 'POST',
        path: registrationsPath,
        body: { user_id: 'u-bruno', date: '2026-11-19', start: '10:00', end: '13:00' },
      })
    })

    const note = 'Always group my registrations in pairs.'
    const absence = 'Absent Mon 16 Nov 2026 – Thu 19 Nov 2026'

    /** The text of the open menu. */
    function menuText(wrapper: Awaited<ReturnType<typeof mountSchedule>['mounting']>) {
      return wrapper.find('[role="dialog"]').text()
    }

    it("hovering an absent member's absence icon shows the absence", async () => {
      const { mounting } = mountSchedule('manager', { memberAbsences: [brunoAway] })
      const wrapper = await mounting

      await open(slotItem(wrapper, 'Thu 19 Nov', '10–13'))
      expect(control(wrapper, absence).attributes('title')).toBe(absence)
      expect(control(wrapper, absence).text()).not.toContain('Bruno')
    })

    it('a member who is not absent has no absence icon', async () => {
      const { mounting } = mountSchedule('manager', {
        memberAbsences: [
          { id: 'ab-chloe', user_id: 'u-chloe', first: '2026-11-20', last: '2026-11-25' },
        ],
      })
      const wrapper = await mounting

      await open(slotItem(wrapper, 'Thu 19 Nov', '10–13'))
      expect(hasControl(wrapper, 'Absent Fri 20 Nov 2026 – Wed 25 Nov 2026')).toBe(false)
    })

    it("hovering a member's note icon shows the note", async () => {
      const { mounting } = mountSchedule('manager', {
        notes: [{ user_id: 'u-bruno', text: note }],
      })
      const wrapper = await mounting

      await open(slotItem(wrapper, 'Thu 19 Nov', '10–13'))
      expect(control(wrapper, note).attributes('title')).toBe(note)
      expect(control(wrapper, note).text()).not.toContain('Bruno')
    })

    it('a member with an empty note has no note icon', async () => {
      const withoutNotes = mountSchedule('manager')
      const without = await withoutNotes.mounting
      await open(slotItem(without, 'Thu 19 Nov', '10–13'))
      const buttons = without.findAll('button').length
      without.unmount()

      const { mounting } = mountSchedule('manager', {
        notes: [{ user_id: 'u-chloe', text: '' }],
      })
      const wrapper = await mounting
      await open(slotItem(wrapper, 'Thu 19 Nov', '10–13'))
      expect(wrapper.findAll('button').length).toBe(buttons)
    })

    it('the texts of the icons are not shown before a click', async () => {
      const { mounting } = mountSchedule('manager', {
        memberAbsences: [brunoAway],
        notes: [{ user_id: 'u-chloe', text: note }],
      })
      const wrapper = await mounting

      await open(slotItem(wrapper, 'Thu 19 Nov', '10–13'))
      expect(menuText(wrapper)).not.toContain(note)
      expect(menuText(wrapper)).not.toContain(absence)
    })

    it('clicking a note icon shows the note under the names, and proposes nothing', async () => {
      const { calls, mounting } = mountSchedule('manager', {
        notes: [{ user_id: 'u-bruno', text: note }],
      })
      const wrapper = await mounting

      await open(slotItem(wrapper, 'Thu 19 Nov', '10–13'))
      await press(wrapper, note)

      expect(menuText(wrapper)).toContain(note)
      expect(hasControl(menu(wrapper), 'Bruno')).toBe(true)
      expect(calls.some((c) => c.method === 'POST')).toBe(false)
    })

    it('clicking an absence icon shows the absence under the names, and proposes nothing', async () => {
      const { calls, mounting } = mountSchedule('manager', { memberAbsences: [brunoAway] })
      const wrapper = await mounting

      await open(slotItem(wrapper, 'Thu 19 Nov', '10–13'))
      await press(wrapper, absence)

      expect(menuText(wrapper)).toContain(absence)
      expect(calls.some((c) => c.method === 'POST')).toBe(false)
    })

    it('clicking the icon whose text is shown hides it', async () => {
      const { mounting } = mountSchedule('manager', {
        notes: [{ user_id: 'u-bruno', text: note }],
      })
      const wrapper = await mounting

      await open(slotItem(wrapper, 'Thu 19 Nov', '10–13'))
      await press(wrapper, note)
      await press(wrapper, note)

      expect(menuText(wrapper)).not.toContain(note)
    })

    it('clicking another icon shows its text in place of the text shown', async () => {
      const { mounting } = mountSchedule('manager', {
        memberAbsences: [brunoAway],
        notes: [{ user_id: 'u-chloe', text: note }],
      })
      const wrapper = await mounting

      await open(slotItem(wrapper, 'Thu 19 Nov', '10–13'))
      await press(wrapper, note)
      await press(wrapper, absence)

      expect(menuText(wrapper)).toContain(absence)
      expect(menuText(wrapper)).not.toContain(note)
    })

    it('the absence icon in French', async () => {
      localStorage.setItem('gilda.locale', 'fr')
      const { mounting } = mountSchedule('manager', { memberAbsences: [brunoAway] })
      const wrapper = await mounting

      await open(slotItem(wrapper, 'jeu. 19 nov.', '10–13'))
      const french = 'Absent du lun. 16 nov. 2026 au jeu. 19 nov. 2026'
      expect(control(wrapper, french).attributes('title')).toBe(french)
    })

    it('a volunteer does not load the absences and notes of the members', async () => {
      const { calls, mounting } = mountSchedule('volunteer')
      const wrapper = await mounting

      await open(slotItem(wrapper, 'Thu 19 Nov', '10–13'))
      expect(hasControl(wrapper, 'Sign up')).toBe(true)
      expect(calls.some((c) => c.path.endsWith('/member-absences'))).toBe(false)
      expect(calls.some((c) => c.path.endsWith('/notes'))).toBe(false)
    })
  })

  describe('R27', () => {
    const planningPeriod = { first: '2026-11-02', last: '2026-11-25' }

    /** The display names of the menu's buttons proposing the occurrence, in order. */
    async function namesOn(
      overrides: Parameters<typeof mountSchedule>[1],
      dayLabel = 'Thu 19 Nov',
    ) {
      const { mounting } = mountSchedule('manager', overrides)
      const wrapper = await mounting
      await open(slotItem(wrapper, dayLabel, '10–13'))
      return menu(wrapper)
        .findAll('button')
        .map((b) => b.text().trim())
        .filter((t) => /^(Alice|Bruno|Chloé)( \(\d+\))?$/.test(t))
        .map((t) => t.replace(/ \(\d+\)$/, ''))
    }

    it('Preferred, then Possible, then none stated', async () => {
      const names = await namesOn({
        preferences: [
          { user_id: 'u-alice', slot_id: 's-thu', value: 'possible' },
          { user_id: 'u-chloe', slot_id: 's-thu', value: 'preferred' },
        ],
      })
      expect(names).toEqual(['Chloé', 'Alice', 'Bruno'])
    })

    it('none stated, then Unavailable', async () => {
      const names = await namesOn({
        preferences: [
          { user_id: 'u-alice', slot_id: 's-thu', value: 'unavailable' },
          { user_id: 'u-chloe', slot_id: 's-thu', value: 'preferred' },
        ],
      })
      expect(names).toEqual(['Chloé', 'Bruno', 'Alice'])
    })

    it("follows the preferences for the occurrence's slot", async () => {
      const names = await namesOn(
        {
          preferences: [
            { user_id: 'u-alice', slot_id: 's-thu', value: 'preferred' },
            { user_id: 'u-chloe', slot_id: 's-thu', value: 'unavailable' },
            { user_id: 'u-chloe', slot_id: 's-sat', value: 'preferred' },
          ],
        },
        'Sat 21 Nov',
      )
      expect(names).toEqual(['Chloé', 'Alice', 'Bruno'])
    })

    it('absent members come last, whatever their preference', async () => {
      const names = await namesOn({
        preferences: [
          { user_id: 'u-alice', slot_id: 's-thu', value: 'unavailable' },
          { user_id: 'u-bruno', slot_id: 's-thu', value: 'preferred' },
        ],
        memberAbsences: [
          { id: 'ab-bruno', user_id: 'u-bruno', first: '2026-11-19', last: '2026-11-19' },
        ],
      })
      expect(names).toEqual(['Chloé', 'Alice', 'Bruno'])
    })

    it('then by fewest registrations', async () => {
      const names = await namesOn({
        planningPeriod,
        registrationCounts: [
          { user_id: 'u-alice', count: 2 },
          { user_id: 'u-bruno', count: 0 },
          { user_id: 'u-chloe', count: 1 },
        ],
      })
      expect(names).toEqual(['Bruno', 'Chloé', 'Alice'])
    })

    it('the preference comes before the registrations', async () => {
      const names = await namesOn({
        planningPeriod,
        preferences: [{ user_id: 'u-chloe', slot_id: 's-thu', value: 'preferred' }],
        registrationCounts: [
          { user_id: 'u-alice', count: 0 },
          { user_id: 'u-bruno', count: 1 },
          { user_id: 'u-chloe', count: 2 },
        ],
      })
      expect(names).toEqual(['Chloé', 'Alice', 'Bruno'])
    })

    it('absent members are sorted by fewest registrations too', async () => {
      const names = await namesOn({
        planningPeriod,
        registrationCounts: [
          { user_id: 'u-alice', count: 0 },
          { user_id: 'u-bruno', count: 2 },
          { user_id: 'u-chloe', count: 1 },
        ],
        memberAbsences: [
          { id: 'ab-bruno', user_id: 'u-bruno', first: '2026-11-19', last: '2026-11-19' },
          { id: 'ab-chloe', user_id: 'u-chloe', first: '2026-11-19', last: '2026-11-19' },
        ],
      })
      expect(names).toEqual(['Alice', 'Chloé', 'Bruno'])
    })

    it('then by display name', async () => {
      const names = await namesOn({ members: [chloe, bruno, alice] })
      expect(names).toEqual(['Alice', 'Bruno', 'Chloé'])
    })

    it('then by display name, with equal registrations', async () => {
      const names = await namesOn({
        members: [chloe, bruno, alice],
        planningPeriod,
        registrationCounts: [
          { user_id: 'u-alice', count: 1 },
          { user_id: 'u-bruno', count: 1 },
          { user_id: 'u-chloe', count: 1 },
        ],
      })
      expect(names).toEqual(['Alice', 'Bruno', 'Chloé'])
    })
  })
})
