import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mountApp, pageText } from '../mountApp'
import { control, hasControl, header, mockApi, press } from '../mockApi'
import { garden, member, signedInAsAlice } from './fixtures'
import {
  day,
  hasDay,
  open,
  planningApi,
  slotItem,
  type Closure,
  type Occurrence,
  type PlanningPeriod,
  type Registration,
} from './planningFake'

const alice = member('u-alice', 'Alice', 'volunteer')
const bruno = member('u-bruno', 'Bruno', 'volunteer')
const chloe = member('u-chloe', 'Chloé', 'volunteer')
const path = `/associations/${garden.id}`
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
  } = {},
  at = path,
) {
  const api = planningApi({
    me: alice.user_id,
    role,
    members: [{ ...alice, role }, bruno, chloe],
    occurrences: overrides.occurrences ?? occurrences(['2026-11-14']),
    registrations: overrides.registrations ?? registrations.map((r) => ({ ...r })),
    closures: [closure],
    planningPeriod: overrides.planningPeriod ?? null,
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

  it('"Members" and "Schedule settings" lead to those screens', async () => {
    const { mounting } = mountSchedule()
    const wrapper = await mounting

    expect(control(wrapper, 'Members').attributes('href')).toBe(`${path}/members`)
    expect(control(wrapper, 'Schedule settings').attributes('href')).toBe(`${path}/settings`)
  })

  it('week headings show only the week number', async () => {
    const { mounting } = mountSchedule()
    const text = pageText(await mounting)

    expect(text).toContain('Week 44')
    expect(text).not.toContain('26 Oct – 1 Nov')
  })

  it('no longer opens at /associations/{id}/schedule', async () => {
    const { mounting } = mountSchedule('volunteer', {}, `${path}/schedule`)
    const text = pageText(await mounting)

    expect(text).not.toContain('Week 44')
  })

  it('opens on the week before the current one and shows six weeks', async () => {
    const { api, mounting } = mountSchedule()
    const wrapper = await mounting

    expect(api.scheduleRequests).toContainEqual({ from: '2026-10-19', to: '2026-11-29' })
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

  it("an occurrence shows its times and its registration's display name", async () => {
    const { mounting } = mountSchedule()
    const wrapper = await mounting

    const occurrence = slotItem(wrapper, 'Thu 29 Oct', '10–13')
    expect(occurrence.text()).toContain('Chloé')
    expect(occurrence.text()).not.toMatch(/Chloé\s*\?/)
  })

  it('a proposed registration shows "?"', async () => {
    const { mounting } = mountSchedule()

    expect(slotItem(await mounting, 'Sat 31 Oct', '10–13').text()).toMatch(/Alice\s*\?/)
  })

  it('an occurrence without registration shows its times only', async () => {
    const { mounting } = mountSchedule()

    expect(
      slotItem(await mounting, 'Thu 19 Nov', '10–13')
        .text()
        .trim(),
    ).toBe('10–13')
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

      const line = text.indexOf('Planning period · from Wednesday 4 November 2026')
      expect(line).toBeGreaterThan(text.indexOf('Week 44'))
      expect(line).toBeLessThan(text.indexOf('Week 45'))
    })

    it('a line marked with the last date sits just after the week that holds it', async () => {
      const { mounting } = mountSchedule('volunteer', { planningPeriod: period })
      const text = pageText(await mounting)

      const line = text.indexOf('End of planning period · Wednesday 18 November 2026')
      expect(line).toBeGreaterThan(text.indexOf('Week 47'))
      expect(line).toBeLessThan(text.indexOf('Week 48'))
    })

    it('the today line comes first when the first line falls at the same place', async () => {
      const { mounting } = mountSchedule('volunteer', {
        planningPeriod: { first: '2026-10-26', last: '2026-11-18' },
      })
      const text = pageText(await mounting)

      const today = text.indexOf('Today · Wednesday 28 October 2026')
      const first = text.indexOf('Planning period · from Monday 26 October 2026')
      expect(today).toBeGreaterThan(text.indexOf('Week 43'))
      expect(first).toBeGreaterThan(today)
      expect(first).toBeLessThan(text.indexOf('Week 44'))
    })

    it('the schedule opens far enough to show the week after the one holding the last date', async () => {
      const { api, mounting } = mountSchedule('volunteer', {
        planningPeriod: { first: '2026-11-04', last: '2026-11-25' },
      })
      const text = pageText(await mounting)

      expect(api.scheduleRequests).toContainEqual({ from: '2026-10-19', to: '2026-12-06' })
      for (const week of [43, 48, 49]) expect(text).toContain(`Week ${week}`)
      expect(text).not.toContain('Week 50')
    })

    it('a last date on a Sunday still brings the week after', async () => {
      const { mounting } = mountSchedule('volunteer', {
        planningPeriod: { first: '2026-11-04', last: '2026-12-13' },
      })
      const text = pageText(await mounting)

      expect(text).toContain('Week 51')
      expect(text).not.toContain('Week 52')
    })

    it('six weeks stay six when they already reach the week after', async () => {
      const { api, mounting } = mountSchedule('volunteer', { planningPeriod: period })
      const text = pageText(await mounting)

      expect(api.scheduleRequests).toContainEqual({ from: '2026-10-19', to: '2026-11-29' })
      expect(text).not.toContain('Week 49')
    })

    it('shows no line without a period', async () => {
      const { mounting } = mountSchedule()
      const text = pageText(await mounting)

      expect(text).not.toContain('Planning period')
      expect(text).not.toContain('End of planning period')
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
      expect(hasControl(wrapper, 'Chloé')).toBe(true)
      await press(wrapper, 'Bruno')

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
})
