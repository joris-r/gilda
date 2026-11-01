import type { DOMWrapper, VueWrapper } from '@vue/test-utils'
import { flushPromises } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mountApp, pageText } from '../mountApp'
import { field, fill, hasControl, header, item, mockApi, press } from '../mockApi'
import { garden, member, signedInAsAlice } from './fixtures'
import { planningApi, preferenceOf, type Preference, type PlanningPeriod } from './planningFake'

const path = `/associations/${garden.id}/settings`
const base = `/api/associations/${garden.id}`

function mountSettings(
  role: 'manager' | 'volunteer',
  planningPeriod: PlanningPeriod | null = { first: '2026-11-02', last: '2026-11-25' },
  preferences: Preference[] = [],
) {
  const api = planningApi({
    me: 'u-alice',
    role,
    members: [
      member('u-alice', 'Alice', role),
      member('u-bruno', 'Bruno', 'volunteer'),
      member('u-chloe', 'Chloé', 'volunteer'),
    ],
    preferences,
    slots: [
      { id: 's-sat', weekday: 'saturday', start: '10:00', end: '13:00' },
      { id: 's-thu', weekday: 'thursday', start: '10:00', end: '13:00' },
    ],
    closures: [
      { id: 'c-fete', first: '2026-11-14', last: '2026-11-14', label: 'Fête du quartier' },
      { id: 'c-noel', first: '2026-12-24', last: '2027-01-01', label: "Fêtes de fin d'année" },
    ],
    planningPeriod,
  })
  const calls = mockApi({ 'GET /api/session': signedInAsAlice, ...api.routes })
  return { calls, mounting: mountApp(path) }
}

/** The "My preference" selector of the slot listed with `weekday`. */
function myPreference(wrapper: VueWrapper, weekday: string) {
  return field(item(wrapper, weekday), 'My preference')
}

/** The selected option's text of a selector. */
function shown(select: DOMWrapper<Element>) {
  const element = select.element as HTMLSelectElement
  return element.options[element.selectedIndex]?.text.trim()
}

/** The rows of "Members' preferences", by member display name, each with its selectors. */
function memberPreferences(wrapper: VueWrapper) {
  const table = wrapper.find('table')
  const rows = table.findAll('tr').filter((tr) => tr.find('select').exists())
  return {
    table,
    names: rows.map((tr) => tr.find('th, td').text().trim()),
    cell(name: string, column: number) {
      const row = rows.find((tr) => tr.find('th, td').text().trim() === name)
      if (row === undefined) throw new Error(`No row "${name}"`)
      return row.findAll('select')[column]
    },
  }
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

describe('Schedule settings', () => {
  it('the header shows the association name, then Schedule settings', async () => {
    const { mounting } = mountSettings('manager')
    const text = header(await mounting).text()

    expect(text).toContain(garden.name)
    expect(text.indexOf('Schedule settings')).toBeGreaterThan(text.indexOf(garden.name))
  })

  it('in French, the screen is "Réglages du planning"', async () => {
    localStorage.setItem('gilda.locale', 'fr')
    const { mounting } = mountSettings('manager')

    expect(header(await mounting).text()).toContain('Réglages du planning')
  })

  it('shows no back link', async () => {
    const { mounting } = mountSettings('manager')

    const text = pageText(await mounting)

    expect(text).toContain('Fête du quartier')
    expect(text).not.toContain('←')
  })

  it('no longer opens at /associations/{id}/opening', async () => {
    const api = planningApi({ me: 'u-alice', role: 'manager', members: [] })
    mockApi({ 'GET /api/session': signedInAsAlice, ...api.routes })
    const wrapper = await mountApp(`/associations/${garden.id}/opening`)

    expect(hasControl(wrapper, 'Add slot')).toBe(false)
  })

  it('shows Planning period, then Closures, then Slots', async () => {
    const { mounting } = mountSettings('manager')
    const wrapper = await mounting

    const sections = wrapper
      .findAll('h1, h2, h3')
      .map((h) => h.text().trim())
      .filter((text) => ['Planning period', 'Closures', 'Slots'].includes(text))
    expect(sections).toEqual(['Planning period', 'Closures', 'Slots'])
  })

  it('lists the slots, with their day and times', async () => {
    const { mounting } = mountSettings('manager')
    const wrapper = await mounting

    expect(item(wrapper, 'Thursday').text()).toContain('10:00–13:00')
    expect(item(wrapper, 'Saturday').text()).toContain('10:00–13:00')
  })

  it('lists the closures, with their dates and label', async () => {
    const { mounting } = mountSettings('manager')
    const wrapper = await mounting

    expect(item(wrapper, 'Fête du quartier').text()).toContain('Sat 14 Nov 2026')
    expect(item(wrapper, "Fêtes de fin d'année").text()).toContain(
      'Thu 24 Dec 2026 – Fri 1 Jan 2027',
    )
  })

  describe('as a manager', () => {
    it('adds a slot with POST', async () => {
      const { calls, mounting } = mountSettings('manager')
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

    describe('Add slot defaults', () => {
      /** The current value of the Add slot field `label`. */
      function valueOf(slotForm: DOMWrapper<Element>, label: string) {
        return (field(slotForm, label).element as HTMLInputElement).value
      }

      it('R17: opens with From and To at 09:00', async () => {
        const { mounting } = mountSettings('manager')
        const slotForm = form(await mounting, 'Add slot')

        expect(valueOf(slotForm, 'From')).toBe('09:00')
        expect(valueOf(slotForm, 'To')).toBe('09:00')
      })

      it('R17: changing From sets To to the same time', async () => {
        const { mounting } = mountSettings('manager')
        const slotForm = form(await mounting, 'Add slot')

        await fill(slotForm, 'From', '14:00')

        expect(valueOf(slotForm, 'To')).toBe('14:00')
      })

      it('R17: once To is changed, changing From leaves To as it is', async () => {
        const { mounting } = mountSettings('manager')
        const slotForm = form(await mounting, 'Add slot')

        await fill(slotForm, 'To', '12:00')
        await fill(slotForm, 'From', '10:00')

        expect(valueOf(slotForm, 'From')).toBe('10:00')
        expect(valueOf(slotForm, 'To')).toBe('12:00')
      })

      it("R18: after a slot is added, Day keeps its value and From and To show the slot's end", async () => {
        const { mounting } = mountSettings('manager')
        const wrapper = await mounting
        const slotForm = form(wrapper, 'Add slot')

        await fill(slotForm, 'Day', 'friday')
        await fill(slotForm, 'From', '16:00')
        await fill(slotForm, 'To', '19:00')
        await press(slotForm, 'Add slot')
        await flushPromises()

        expect(valueOf(slotForm, 'Day')).toBe('friday')
        expect(valueOf(slotForm, 'From')).toBe('19:00')
        expect(valueOf(slotForm, 'To')).toBe('19:00')
      })

      it('R18: after a slot is added, To follows From again', async () => {
        const { mounting } = mountSettings('manager')
        const wrapper = await mounting
        const slotForm = form(wrapper, 'Add slot')

        await fill(slotForm, 'To', '13:00')
        await press(slotForm, 'Add slot')
        await flushPromises()
        await fill(slotForm, 'From', '15:00')

        expect(valueOf(slotForm, 'To')).toBe('15:00')
      })
    })

    it('deletes a slot with DELETE', async () => {
      const { calls, mounting } = mountSettings('manager')
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
      const { calls, mounting } = mountSettings('manager')
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
      const { calls, mounting } = mountSettings('manager')
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
      const { calls, mounting } = mountSettings('manager')
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

  describe('planning period, as a manager', () => {
    it('sets the planning period with PUT', async () => {
      const { calls, mounting } = mountSettings('manager', null)
      const wrapper = await mounting
      const periodForm = form(wrapper, 'Save')

      await fill(periodForm, 'From', '2026-11-30')
      await fill(periodForm, 'To', '2026-12-20')
      await press(periodForm, 'Save')

      expect(calls).toContainEqual({
        method: 'PUT',
        path: `${base}/planning-period`,
        body: { first: '2026-11-30', last: '2026-12-20' },
      })
    })

    it('clears the planning period with DELETE', async () => {
      const { calls, mounting } = mountSettings('manager')
      const wrapper = await mounting

      await press(wrapper, 'Clear')

      expect(calls).toContainEqual({
        method: 'DELETE',
        path: `${base}/planning-period`,
        body: undefined,
      })
    })
  })

  describe('planning period, as a volunteer', () => {
    it('shows the period, without the form', async () => {
      const { mounting } = mountSettings('volunteer')
      const wrapper = await mounting

      expect(pageText(wrapper)).toContain('Planning period')
      expect(pageText(wrapper)).toContain('Mon 2 Nov 2026 – Wed 25 Nov 2026')
      expect(hasControl(wrapper, 'Save')).toBe(false)
      expect(hasControl(wrapper, 'Clear')).toBe(false)
    })

    it('shows "None" when there is no period', async () => {
      const { mounting } = mountSettings('volunteer', null)
      const wrapper = await mounting

      expect(pageText(wrapper)).toContain('None')
    })
  })

  it('a volunteer sees the lists, without Delete and without the forms', async () => {
    const { mounting } = mountSettings('volunteer')
    const wrapper = await mounting

    expect(item(wrapper, 'Thursday').text()).toContain('10:00–13:00')
    expect(item(wrapper, 'Fête du quartier').exists()).toBe(true)
    expect(hasControl(wrapper, 'Delete')).toBe(false)
    expect(hasControl(wrapper, 'Add slot')).toBe(false)
    expect(hasControl(wrapper, 'Add closure')).toBe(false)
  })

  describe('My preference', () => {
    it.each(['manager', 'volunteer'] as const)(
      'a %s sees their own preference on each slot, "—" when none',
      async (role) => {
        const { mounting } = mountSettings(role, null, [
          { user_id: 'u-alice', slot_id: 's-thu', value: 'preferred' },
          { user_id: 'u-bruno', slot_id: 's-sat', value: 'unavailable' },
        ])
        const wrapper = await mounting

        expect(shown(myPreference(wrapper, 'Thursday'))).toBe('Preferred')
        expect(shown(myPreference(wrapper, 'Saturday'))).toBe('—')
      },
    )

    it('offers "—", Preferred, Possible and Unavailable', async () => {
      const { mounting } = mountSettings('volunteer')
      const wrapper = await mounting

      const options = myPreference(wrapper, 'Thursday')
        .findAll('option')
        .map((o) => o.text().trim())
      expect(options).toEqual(['—', 'Preferred', 'Possible', 'Unavailable'])
    })

    it('choosing a value saves it at once with PUT', async () => {
      const { calls, mounting } = mountSettings('volunteer')
      const wrapper = await mounting

      await myPreference(wrapper, 'Thursday').setValue('possible')
      await flushPromises()

      expect(calls).toContainEqual({
        method: 'PUT',
        path: `${base}/preferences/s-thu/u-alice`,
        body: { value: 'possible' },
      })
    })

    it('choosing "—" deletes it with DELETE', async () => {
      const { calls, mounting } = mountSettings('volunteer', null, [
        { user_id: 'u-alice', slot_id: 's-thu', value: 'preferred' },
      ])
      const wrapper = await mounting

      const select = myPreference(wrapper, 'Thursday')
      const none = select.findAll('option').find((o) => o.text().trim() === '—')!
      await select.setValue((none.element as HTMLOptionElement).value)
      await flushPromises()

      expect(calls).toContainEqual({
        method: 'DELETE',
        path: `${base}/preferences/s-thu/u-alice`,
        body: undefined,
      })
    })

    it('the selector is marked with its value, unmarked for "—"', async () => {
      const { mounting } = mountSettings('volunteer', null, [
        { user_id: 'u-alice', slot_id: 's-thu', value: 'unavailable' },
      ])
      const wrapper = await mounting

      expect(preferenceOf(myPreference(wrapper, 'Thursday'))).toBe('unavailable')
      expect(preferenceOf(myPreference(wrapper, 'Saturday'))).toBeNull()

      await myPreference(wrapper, 'Saturday').setValue('preferred')
      await flushPromises()

      expect(preferenceOf(myPreference(wrapper, 'Saturday'))).toBe('preferred')
    })

    it('in French, "Mes préférences" and the values', async () => {
      localStorage.setItem('gilda.locale', 'fr')
      const { mounting } = mountSettings('volunteer')
      const wrapper = await mounting

      expect(pageText(wrapper)).toContain('Mes préférences')
      const options = wrapper
        .find('li select')
        .findAll('option')
        .map((o) => o.text().trim())
      expect(options).toEqual(['—', 'Préféré', 'Possible', 'Indisponible'])
    })
  })

  describe("Members' preferences", () => {
    const set: Preference[] = [
      { user_id: 'u-alice', slot_id: 's-thu', value: 'preferred' },
      { user_id: 'u-bruno', slot_id: 's-thu', value: 'possible' },
      { user_id: 'u-bruno', slot_id: 's-sat', value: 'unavailable' },
      { user_id: 'u-chloe', slot_id: 's-sat', value: 'preferred' },
    ]

    it('a manager sees one row per member and one column per slot', async () => {
      const { mounting } = mountSettings('manager', null, set)
      const wrapper = await mounting
      const grid = memberPreferences(wrapper)

      expect(pageText(wrapper)).toContain("Members' preferences")
      expect(grid.names).toEqual(['Alice', 'Bruno', 'Chloé'])
      const header = grid.table.find('tr').text()
      expect(header.indexOf('Thu')).toBeGreaterThanOrEqual(0)
      expect(header.indexOf('Sat')).toBeGreaterThan(header.indexOf('Thu'))
      expect(shown(grid.cell('Alice', 0))).toBe('Preferred')
      expect(shown(grid.cell('Alice', 1))).toBe('—')
      expect(shown(grid.cell('Bruno', 0))).toBe('Possible')
      expect(shown(grid.cell('Bruno', 1))).toBe('Unavailable')
      expect(shown(grid.cell('Chloé', 0))).toBe('—')
      expect(shown(grid.cell('Chloé', 1))).toBe('Preferred')
    })

    it('each cell is marked with its value', async () => {
      const { mounting } = mountSettings('manager', null, set)
      const grid = memberPreferences(await mounting)

      expect(preferenceOf(grid.cell('Bruno', 0))).toBe('possible')
      expect(preferenceOf(grid.cell('Bruno', 1))).toBe('unavailable')
      expect(preferenceOf(grid.cell('Chloé', 0))).toBeNull()
    })

    it("a cell saves another member's preference at once with PUT", async () => {
      const { calls, mounting } = mountSettings('manager', null, set)
      const wrapper = await mounting

      await memberPreferences(wrapper).cell('Chloé', 0).setValue('unavailable')
      await flushPromises()

      expect(calls).toContainEqual({
        method: 'PUT',
        path: `${base}/preferences/s-thu/u-chloe`,
        body: { value: 'unavailable' },
      })
    })

    it('a cell set to "—" deletes the preference with DELETE', async () => {
      const { calls, mounting } = mountSettings('manager', null, set)
      const wrapper = await mounting

      const cell = memberPreferences(wrapper).cell('Bruno', 1)
      const none = cell.findAll('option').find((o) => o.text().trim() === '—')!
      await cell.setValue((none.element as HTMLOptionElement).value)
      await flushPromises()

      expect(calls).toContainEqual({
        method: 'DELETE',
        path: `${base}/preferences/s-sat/u-bruno`,
        body: undefined,
      })
    })

    it('in French, "Préférences des membres"', async () => {
      localStorage.setItem('gilda.locale', 'fr')
      const { mounting } = mountSettings('manager', null, set)

      expect(pageText(await mounting)).toContain('Préférences des membres')
    })

    it('is not shown to a volunteer', async () => {
      const { mounting } = mountSettings('volunteer', null, set)
      const wrapper = await mounting

      expect(pageText(wrapper)).toContain('Thursday')
      expect(pageText(wrapper)).not.toContain("Members' preferences")
      expect(wrapper.find('table').exists()).toBe(false)
    })
  })
})
