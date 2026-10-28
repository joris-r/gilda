import type { VueWrapper } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mountApp, pageText } from '../mountApp'
import { fill, hasControl, item, mockApi, press } from '../mockApi'
import { garden, member, signedInAsAlice } from './fixtures'
import { planningApi } from './planningFake'

const path = `/associations/${garden.id}/opening`
const base = `/api/associations/${garden.id}`

function mountOpening(role: 'manager' | 'volunteer') {
  const api = planningApi({
    me: 'u-alice',
    role,
    members: [member('u-alice', 'Alice', role)],
    slots: [
      { id: 's-sat', weekday: 'saturday', start: '10:00', end: '13:00' },
      { id: 's-thu', weekday: 'thursday', start: '10:00', end: '13:00' },
    ],
    closures: [
      { id: 'c-fete', first: '2026-11-14', last: '2026-11-14', label: 'Fête du quartier' },
      { id: 'c-noel', first: '2026-12-24', last: '2027-01-01', label: "Fêtes de fin d'année" },
    ],
  })
  const calls = mockApi({ 'GET /api/session': signedInAsAlice, ...api.routes })
  return { calls, mounting: mountApp(path) }
}

/** The form holding the button `submit`. */
function form(wrapper: VueWrapper, submit: string) {
  const found = wrapper.findAll('form').find((f) => hasControl(f, submit))
  if (found === undefined) throw new Error(`No form with "${submit}"`)
  return found
}

beforeEach(() => {
  localStorage.clear()
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('Opening hours', () => {
  it('lists the slots, with their day and times', async () => {
    const { mounting } = mountOpening('manager')
    const wrapper = await mounting

    expect(item(wrapper, 'Thursday').text()).toContain('10:00–13:00')
    expect(item(wrapper, 'Saturday').text()).toContain('10:00–13:00')
  })

  it('lists the closures, with their dates and label', async () => {
    const { mounting } = mountOpening('manager')
    const wrapper = await mounting

    expect(item(wrapper, 'Fête du quartier').text()).toContain('Sat 14 Nov 2026')
    expect(item(wrapper, "Fêtes de fin d'année").text()).toContain(
      'Thu 24 Dec 2026 – Fri 1 Jan 2027',
    )
  })

  describe('as a manager', () => {
    it('adds a slot with POST', async () => {
      const { calls, mounting } = mountOpening('manager')
      const wrapper = await mounting
      const slotForm = form(wrapper, 'Add slot')

      await fill(slotForm, 'Day', 'friday')
      await fill(slotForm, 'From', '16:00')
      await fill(slotForm, 'To', '19:00')
      await press(slotForm, 'Add slot')

      expect(calls).toContainEqual({
        method: 'POST',
        path: `${base}/slots`,
        body: { weekday: 'friday', start: '16:00', end: '19:00' },
      })
      expect(item(wrapper, 'Friday').text()).toContain('16:00–19:00')
    })

    it('deletes a slot with DELETE', async () => {
      const { calls, mounting } = mountOpening('manager')
      const wrapper = await mounting

      await press(item(wrapper, 'Thursday'), 'Delete')

      expect(calls).toContainEqual({
        method: 'DELETE',
        path: `${base}/slots/s-thu`,
        body: undefined,
      })
      expect(wrapper.findAll('li').some((li) => li.text().includes('Thursday'))).toBe(false)
    })

    it('adds a closure with POST', async () => {
      const { calls, mounting } = mountOpening('manager')
      const wrapper = await mounting
      const closureForm = form(wrapper, 'Add closure')

      await fill(closureForm, 'From', '2027-02-15')
      await fill(closureForm, 'To', '2027-02-19')
      await fill(closureForm, 'Label', "Vacances d'hiver")
      await press(closureForm, 'Add closure')

      expect(calls).toContainEqual({
        method: 'POST',
        path: `${base}/closures`,
        body: { first: '2027-02-15', last: '2027-02-19', label: "Vacances d'hiver" },
      })
      expect(item(wrapper, "Vacances d'hiver").text()).toContain(
        'Mon 15 Feb 2027 – Fri 19 Feb 2027',
      )
    })

    it('adds a closure without label', async () => {
      const { calls, mounting } = mountOpening('manager')
      const wrapper = await mounting
      const closureForm = form(wrapper, 'Add closure')

      await fill(closureForm, 'From', '2027-03-01')
      await fill(closureForm, 'To', '2027-03-01')
      await press(closureForm, 'Add closure')

      const post = calls.find((c) => c.method === 'POST' && c.path === `${base}/closures`)
      const body = post?.body as { first: string; last: string; label?: string | null }
      expect(body.first).toBe('2027-03-01')
      expect(body.label ?? null).toBeNull()
      expect(pageText(wrapper)).toContain('Mon 1 Mar 2027')
    })

    it('deletes a closure with DELETE', async () => {
      const { calls, mounting } = mountOpening('manager')
      const wrapper = await mounting

      await press(item(wrapper, 'Fête du quartier'), 'Delete')

      expect(calls).toContainEqual({
        method: 'DELETE',
        path: `${base}/closures/c-fete`,
        body: undefined,
      })
      expect(pageText(wrapper)).not.toContain('Fête du quartier')
    })
  })

  it('a volunteer sees the lists, without Delete and without the forms', async () => {
    const { mounting } = mountOpening('volunteer')
    const wrapper = await mounting

    expect(item(wrapper, 'Thursday').text()).toContain('10:00–13:00')
    expect(item(wrapper, 'Fête du quartier').exists()).toBe(true)
    expect(hasControl(wrapper, 'Delete')).toBe(false)
    expect(hasControl(wrapper, 'Add slot')).toBe(false)
    expect(hasControl(wrapper, 'Add closure')).toBe(false)
  })
})
