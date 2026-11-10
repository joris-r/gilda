import type { DOMWrapper, VueWrapper } from '@vue/test-utils'
import { flushPromises } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mountApp, pageText } from '../mountApp'
import {
  dialog,
  dialogs,
  field,
  fill,
  hasControl,
  header,
  item,
  mockApi,
  press,
  pressEscape,
  showsControl,
  showsField,
  titleOf,
  type Route,
} from '../mockApi'
import { garden, member, signedInAsAlice } from './fixtures'
import {
  planningApi,
  preferenceOf,
  type Closure,
  type Preference,
  type PlanningPeriod,
} from './planningFake'

const path = `/association/${garden.slug}/settings`
const base = `/api/associations/${garden.id}`

function mountSettings(
  role: 'manager' | 'volunteer',
  planningPeriod: PlanningPeriod | null = { first: '2026-11-02', last: '2026-11-25' },
  preferences: Preference[] = [],
  routes: Record<string, Route> = {},
  closures: Closure[] = [
    { id: 'c-fete', first: '2026-11-14', last: '2026-11-14', label: 'Fête du quartier' },
    { id: 'c-noel', first: '2026-12-24', last: '2027-01-01', label: "Fêtes de fin d'année" },
  ],
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
    closures,
    planningPeriod,
  })
  const calls = mockApi({ 'GET /api/session': signedInAsAlice, ...api.routes, ...routes })
  return { calls, mounting: mountApp(path) }
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

/** Adds a slot through the Add a slot dialog. */
async function addSlot(wrapper: VueWrapper, weekday: string, start: string, end: string) {
  await press(wrapper, 'Add a slot')
  await fill(dialog(wrapper), 'Day', weekday)
  await fill(dialog(wrapper), 'From', start)
  await fill(dialog(wrapper), 'To', end)
  await press(dialog(wrapper), 'Add slot')
}

beforeEach(() => {
  localStorage.clear()
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('Schedule settings', () => {
  // /core/ui/header/location
  it('the header shows the association name, then Schedule settings', async () => {
    const { mounting } = mountSettings('manager')
    const text = header(await mounting).text()

    expect(text).toContain(garden.name)
    expect(text.indexOf('Schedule settings')).toBeGreaterThan(text.indexOf(garden.name))
  })

  // /planning/ui/schedule-settings/french
  it('in French, the screen is "Réglages du planning"', async () => {
    localStorage.setItem('gilda.locale', 'fr')
    const { mounting } = mountSettings('manager')

    expect(header(await mounting).text()).toContain('Réglages du planning')
  })

  // /core/ui/header/title
  it('shows no back link', async () => {
    const { mounting } = mountSettings('manager')

    const text = pageText(await mounting)

    expect(text).toContain('Fête du quartier')
    expect(text).not.toContain('←')
  })

  // /planning/ui/schedule-settings
  it('no longer opens at /association/{slug}/opening', async () => {
    const api = planningApi({ me: 'u-alice', role: 'manager', members: [] })
    mockApi({ 'GET /api/session': signedInAsAlice, ...api.routes })
    const wrapper = await mountApp(`/association/${garden.slug}/opening`)

    expect(hasControl(wrapper, 'Add a slot')).toBe(false)
  })

  // /planning/ui/schedule-settings/period /planning/ui/schedule-settings/closures /planning/ui/schedule-settings/slots
  it('shows Planning period, then Closures, then Slots', async () => {
    const { mounting } = mountSettings('manager')
    const wrapper = await mounting

    const sections = wrapper
      .findAll('h1, h2, h3')
      .map((h) => h.text().trim())
      .filter((text) => ['Planning period', 'Closures', 'Slots'].includes(text))
    expect(sections).toEqual(['Planning period', 'Closures', 'Slots'])
  })

  // /planning/ui/schedule-settings/slots
  it('lists the slots, with their day and times', async () => {
    const { mounting } = mountSettings('manager')
    const wrapper = await mounting

    expect(item(wrapper, 'Thursday').text()).toContain('10:00–13:00')
    expect(item(wrapper, 'Saturday').text()).toContain('10:00–13:00')
  })

  // /planning/ui/schedule-settings/closures
  it('lists the closures, with their dates and label', async () => {
    const { mounting } = mountSettings('manager')
    const wrapper = await mounting

    expect(item(wrapper, 'Fête du quartier').text()).toContain('Sat 14 Nov 2026')
    expect(item(wrapper, "Fêtes de fin d'année").text()).toContain(
      'Thu 24 Dec 2026 – Fri 1 Jan 2027',
    )
  })

  describe('as a manager', () => {
    // /ui/forms/dialog
    it('shows no form until one is opened', async () => {
      const { mounting } = mountSettings('manager')
      const wrapper = await mounting

      expect(dialogs(wrapper)).toHaveLength(0)
      expect(wrapper.findAll('form')).toHaveLength(0)
      expect(showsField(wrapper, 'Label')).toBe(false)
      expect(showsField(wrapper, 'Day')).toBe(false)
    })

    // /planning/ui/schedule-settings/add-slot /ui/forms/create
    it('"Add a slot" opens the dialog "Add a slot"', async () => {
      const { mounting } = mountSettings('manager')
      const wrapper = await mounting

      await press(wrapper, 'Add a slot')

      const open = dialog(wrapper)
      expect(titleOf(open)).toBe('Add a slot')
      expect(showsField(open, 'Day')).toBe(true)
      expect(showsField(open, 'From')).toBe(true)
      expect(showsField(open, 'To')).toBe(true)
      expect(showsControl(open, 'Add slot')).toBe(true)
    })

    // /planning/ui/schedule-settings/add-slot /ui/forms/success
    it('adds a slot with POST and closes the dialog', async () => {
      const { calls, mounting } = mountSettings('manager')
      const wrapper = await mounting

      await addSlot(wrapper, 'friday', '16:00', '19:00')

      expect(calls).toContainEqual({
        method: 'POST',
        path: `${base}/slots`,
        body: { weekday: 'friday', start: '16:00', end: '19:00' },
      })
      expect(dialogs(wrapper)).toHaveLength(0)
      expect(item(wrapper, 'Friday').text()).toContain('16:00–19:00')
    })

    // /planning/ui/schedule-settings/exists /ui/forms/failure
    it('an existing slot keeps the dialog open, with its message', async () => {
      const { mounting } = mountSettings('manager', undefined, [], {
        [`POST ${base}/slots`]: { status: 409, body: { error: 'Slot exists' } },
      })
      const wrapper = await mounting

      await addSlot(wrapper, 'thursday', '10:00', '13:00')

      expect(titleOf(dialog(wrapper))).toBe('Add a slot')
      expect(dialog(wrapper).text()).toContain('This slot already exists.')
    })

    // /planning/ui/schedule-settings/invalid /ui/forms/failure
    it('a slot refused for its order keeps the dialog open, with its message', async () => {
      const { mounting } = mountSettings('manager', undefined, [], {
        [`POST ${base}/slots`]: { status: 400, body: { error: 'Order' } },
      })
      const wrapper = await mounting

      await addSlot(wrapper, 'thursday', '13:00', '10:00')

      expect(titleOf(dialog(wrapper))).toBe('Add a slot')
      expect(dialog(wrapper).text()).toContain(
        'Check the dates and times: the start comes before the end.',
      )
    })

    // /planning/ui/schedule-settings/invalid /ui/forms/failure
    it('a closure refused for its order keeps the dialog open, with its message', async () => {
      const { mounting } = mountSettings('manager', undefined, [], {
        [`POST ${base}/closures`]: { status: 400, body: { error: 'Order' } },
      })
      const wrapper = await mounting

      await press(wrapper, 'Add a closure')
      await fill(dialog(wrapper), 'From', '2027-02-19')
      await fill(dialog(wrapper), 'To', '2027-02-15')
      await press(dialog(wrapper), 'Add closure')

      expect(titleOf(dialog(wrapper))).toBe('Add a closure')
      expect(dialog(wrapper).text()).toContain(
        'Check the dates and times: the start comes before the end.',
      )
    })

    // /planning/ui/schedule-settings/invalid /ui/forms/failure
    it('a period refused for its order keeps the dialog open, with its message', async () => {
      const { mounting } = mountSettings('manager', null, [], {
        [`PUT ${base}/planning-period`]: { status: 400, body: { error: 'Order' } },
      })
      const wrapper = await mounting

      await press(wrapper, 'Edit the period')
      await fill(dialog(wrapper), 'From', '2026-12-20')
      await fill(dialog(wrapper), 'To', '2026-11-30')
      await press(dialog(wrapper), 'Save')

      expect(titleOf(dialog(wrapper))).toBe('Planning period')
      expect(dialog(wrapper).text()).toContain(
        'Check the dates and times: the start comes before the end.',
      )
    })

    describe('Add a slot defaults', () => {
      /** The current value of the field `label` in the open dialog. */
      function valueOf(wrapper: VueWrapper, label: string) {
        return (field(dialog(wrapper), label).element as HTMLInputElement).value
      }

      // /planning/ui/schedule-settings/defaults
      it('opens with From and To at 09:00', async () => {
        const wrapper = await mountSettings('manager').mounting
        await press(wrapper, 'Add a slot')

        expect(valueOf(wrapper, 'From')).toBe('09:00')
        expect(valueOf(wrapper, 'To')).toBe('09:00')
      })

      // /planning/ui/schedule-settings/defaults
      it('changing From sets To to the same time', async () => {
        const wrapper = await mountSettings('manager').mounting
        await press(wrapper, 'Add a slot')

        await fill(dialog(wrapper), 'From', '14:00')

        expect(valueOf(wrapper, 'To')).toBe('14:00')
      })

      // /planning/ui/schedule-settings/defaults
      it('once To is changed, changing From leaves To as it is', async () => {
        const wrapper = await mountSettings('manager').mounting
        await press(wrapper, 'Add a slot')

        await fill(dialog(wrapper), 'To', '12:00')
        await fill(dialog(wrapper), 'From', '10:00')

        expect(valueOf(wrapper, 'From')).toBe('10:00')
        expect(valueOf(wrapper, 'To')).toBe('12:00')
      })

      // /planning/ui/schedule-settings/next-slot
      it('after a slot is added, the next dialog opens with its Day, and From and To at its end', async () => {
        const wrapper = await mountSettings('manager').mounting

        await addSlot(wrapper, 'friday', '16:00', '19:00')
        await press(wrapper, 'Add a slot')

        expect(valueOf(wrapper, 'Day')).toBe('friday')
        expect(valueOf(wrapper, 'From')).toBe('19:00')
        expect(valueOf(wrapper, 'To')).toBe('19:00')
      })

      // /planning/ui/schedule-settings/next-slot
      it('in the next dialog, To follows From again', async () => {
        const wrapper = await mountSettings('manager').mounting

        await addSlot(wrapper, 'friday', '09:00', '13:00')
        await press(wrapper, 'Add a slot')
        await fill(dialog(wrapper), 'From', '15:00')

        expect(valueOf(wrapper, 'To')).toBe('15:00')
      })
    })

    describe('Edit the slot', () => {
      /** The current value of the field `label` in the open dialog. */
      function valueOf(wrapper: VueWrapper, label: string) {
        return (field(dialog(wrapper), label).element as HTMLInputElement).value
      }

      // /planning/ui/schedule-settings/edit-slot /ui/forms/edit /ui/forms/icon-names
      it('a slot\'s edit icon opens the dialog "Edit the slot", filled with the slot', async () => {
        const wrapper = await mountSettings('manager').mounting

        await press(item(wrapper, 'Thursday'), 'Edit the slot')

        const open = dialog(wrapper)
        expect(titleOf(open)).toBe('Edit the slot')
        expect(valueOf(wrapper, 'Day')).toBe('thursday')
        expect(valueOf(wrapper, 'From')).toBe('10:00')
        expect(valueOf(wrapper, 'To')).toBe('13:00')
        expect(showsControl(open, 'Save')).toBe(true)
      })

      // /planning/ui/schedule-settings/edit-slot
      it('Save edits the slot with PUT and closes the dialog', async () => {
        const { calls, mounting } = mountSettings('manager')
        const wrapper = await mounting

        await press(item(wrapper, 'Thursday'), 'Edit the slot')
        await fill(dialog(wrapper), 'Day', 'friday')
        await fill(dialog(wrapper), 'To', '14:00')
        await press(dialog(wrapper), 'Save')

        expect(calls).toContainEqual({
          method: 'PUT',
          path: `${base}/slots/s-thu`,
          body: { weekday: 'friday', start: '10:00', end: '14:00' },
        })
        expect(dialogs(wrapper)).toHaveLength(0)
        expect(item(wrapper, 'Friday').text()).toContain('10:00–14:00')
        expect(wrapper.findAll('li').some((li) => li.text().includes('Thursday'))).toBe(false)
      })

      // /planning/ui/schedule-settings/edit-exists /ui/forms/failure
      it('an existing slot keeps the dialog open, with its message', async () => {
        const { mounting } = mountSettings('manager', undefined, [], {
          [`PUT ${base}/slots/s-thu`]: { status: 409, body: { error: 'Slot exists' } },
        })
        const wrapper = await mounting

        await press(item(wrapper, 'Thursday'), 'Edit the slot')
        await fill(dialog(wrapper), 'Day', 'saturday')
        await press(dialog(wrapper), 'Save')

        expect(titleOf(dialog(wrapper))).toBe('Edit the slot')
        expect(dialog(wrapper).text()).toContain('This slot already exists.')
      })

      // /planning/ui/schedule-settings/edit-slot
      it('changing From leaves To as it is', async () => {
        const wrapper = await mountSettings('manager').mounting

        await press(item(wrapper, 'Thursday'), 'Edit the slot')
        await fill(dialog(wrapper), 'From', '09:00')

        expect(valueOf(wrapper, 'To')).toBe('13:00')
      })

      // /planning/ui/schedule-settings/defaults
      it('after a slot is edited, Add a slot still opens with its defaults', async () => {
        const wrapper = await mountSettings('manager').mounting

        await press(item(wrapper, 'Thursday'), 'Edit the slot')
        await fill(dialog(wrapper), 'Day', 'friday')
        await press(dialog(wrapper), 'Save')
        await press(wrapper, 'Add a slot')

        expect(valueOf(wrapper, 'From')).toBe('09:00')
        expect(valueOf(wrapper, 'To')).toBe('09:00')
      })
    })

    // /planning/ui/schedule-settings/delete-slot /ui/forms/delete
    it('a slot\'s delete icon asks "Delete the slot Thursday 10:00–13:00?"', async () => {
      const { calls, mounting } = mountSettings('manager')
      const wrapper = await mounting

      await press(item(wrapper, 'Thursday'), 'Delete the slot')

      expect(dialog(wrapper).text()).toContain('Delete the slot Thursday 10:00–13:00?')
      expect(calls.some((c) => c.method === 'DELETE')).toBe(false)
    })

    // /planning/ui/schedule-settings/delete-slot
    it('Delete deletes the slot with DELETE', async () => {
      const { calls, mounting } = mountSettings('manager')
      const wrapper = await mounting

      await press(item(wrapper, 'Thursday'), 'Delete the slot')
      await press(dialog(wrapper), 'Delete')

      expect(calls).toContainEqual({
        method: 'DELETE',
        path: `${base}/slots/s-thu`,
        body: undefined,
      })
      expect(dialogs(wrapper)).toHaveLength(0)
      expect(wrapper.findAll('li').some((li) => li.text().includes('Thursday'))).toBe(false)
    })

    // /ui/forms/close
    it('Cancel keeps the slot', async () => {
      const { calls, mounting } = mountSettings('manager')
      const wrapper = await mounting

      await press(item(wrapper, 'Thursday'), 'Delete the slot')
      await press(dialog(wrapper), 'Cancel')

      expect(calls.some((c) => c.method === 'DELETE')).toBe(false)
      expect(dialogs(wrapper)).toHaveLength(0)
      expect(item(wrapper, 'Thursday').exists()).toBe(true)
    })

    // /planning/ui/schedule-settings/add-closure
    it('"Add a closure" opens the dialog "Add a closure"', async () => {
      const { mounting } = mountSettings('manager')
      const wrapper = await mounting

      await press(wrapper, 'Add a closure')

      const open = dialog(wrapper)
      expect(titleOf(open)).toBe('Add a closure')
      expect(showsField(open, 'From')).toBe(true)
      expect(showsField(open, 'To')).toBe(true)
      expect(showsField(open, 'Label')).toBe(true)
      expect(showsControl(open, 'Add closure')).toBe(true)
    })

    // /planning/ui/schedule-settings/add-closure
    it('adds a closure with POST and closes the dialog', async () => {
      const { calls, mounting } = mountSettings('manager')
      const wrapper = await mounting

      await press(wrapper, 'Add a closure')
      await fill(dialog(wrapper), 'From', '2027-02-15')
      await fill(dialog(wrapper), 'To', '2027-02-19')
      await fill(dialog(wrapper), 'Label', "Vacances d'hiver")
      await press(dialog(wrapper), 'Add closure')

      expect(calls).toContainEqual({
        method: 'POST',
        path: `${base}/closures`,
        body: { first: '2027-02-15', last: '2027-02-19', label: "Vacances d'hiver" },
      })
      expect(dialogs(wrapper)).toHaveLength(0)
      expect(item(wrapper, "Vacances d'hiver").text()).toContain(
        'Mon 15 Feb 2027 – Fri 19 Feb 2027',
      )
    })

    // /planning/ui/schedule-settings/add-closure
    it('adds a closure without label', async () => {
      const { calls, mounting } = mountSettings('manager')
      const wrapper = await mounting

      await press(wrapper, 'Add a closure')
      await fill(dialog(wrapper), 'From', '2027-03-01')
      await fill(dialog(wrapper), 'To', '2027-03-01')
      await press(dialog(wrapper), 'Add closure')

      const post = calls.find((c) => c.method === 'POST' && c.path === `${base}/closures`)
      const body = post?.body as { first: string; last: string; label?: string | null }
      expect(body.first).toBe('2027-03-01')
      expect(body.label ?? null).toBeNull()
      expect(pageText(wrapper)).toContain('Mon 1 Mar 2027')
    })

    // /planning/ui/schedule-settings/edit-closure
    it('a closure\'s edit icon opens the dialog "Edit the closure", filled with the closure', async () => {
      const wrapper = await mountSettings('manager').mounting

      await press(item(wrapper, 'Fête du quartier'), 'Edit the closure')

      const open = dialog(wrapper)
      const valueOf = (label: string) => (field(open, label).element as HTMLInputElement).value
      expect(titleOf(open)).toBe('Edit the closure')
      expect(valueOf('From')).toBe('2026-11-14')
      expect(valueOf('To')).toBe('2026-11-14')
      expect(valueOf('Label')).toBe('Fête du quartier')
      expect(showsControl(open, 'Save')).toBe(true)
    })

    // /planning/ui/schedule-settings/edit-closure
    it('Save edits the closure with PUT and closes the dialog', async () => {
      const { calls, mounting } = mountSettings('manager')
      const wrapper = await mounting

      await press(item(wrapper, 'Fête du quartier'), 'Edit the closure')
      await fill(dialog(wrapper), 'To', '2026-11-15')
      await fill(dialog(wrapper), 'Label', 'Fête du quartier élargie')
      await press(dialog(wrapper), 'Save')

      expect(calls).toContainEqual({
        method: 'PUT',
        path: `${base}/closures/c-fete`,
        body: { first: '2026-11-14', last: '2026-11-15', label: 'Fête du quartier élargie' },
      })
      expect(dialogs(wrapper)).toHaveLength(0)
      expect(item(wrapper, 'Fête du quartier élargie').text()).toContain(
        'Sat 14 Nov 2026 – Sun 15 Nov 2026',
      )
    })

    // /planning/ui/schedule-settings/edit-closure
    it('Save with the label emptied removes it', async () => {
      const { calls, mounting } = mountSettings('manager')
      const wrapper = await mounting

      await press(item(wrapper, 'Fête du quartier'), 'Edit the closure')
      await fill(dialog(wrapper), 'Label', '')
      await press(dialog(wrapper), 'Save')

      const put = calls.find((c) => c.method === 'PUT' && c.path === `${base}/closures/c-fete`)
      const body = put?.body as { label?: string | null }
      expect(body.label ?? null).toBeNull()
      expect(pageText(wrapper)).not.toContain('Fête du quartier')
    })

    // /planning/ui/schedule-settings/delete-closure
    it('a closure\'s delete icon asks "Delete the closure "Fête du quartier"?"', async () => {
      const { calls, mounting } = mountSettings('manager')
      const wrapper = await mounting

      await press(item(wrapper, 'Fête du quartier'), 'Delete the closure')

      expect(dialog(wrapper).text()).toContain('Delete the closure "Fête du quartier"?')
      expect(calls.some((c) => c.method === 'DELETE')).toBe(false)
    })

    // /planning/ui/schedule-settings/delete-closure
    it('without a label, it asks "Delete the closure of Sat 14 Nov 2026?"', async () => {
      const { mounting } = mountSettings('manager', undefined, [], {}, [
        { id: 'c-fete', first: '2026-11-14', last: '2026-11-14', label: null },
      ])
      const wrapper = await mounting

      await press(item(wrapper, 'Sat 14 Nov 2026'), 'Delete the closure')

      expect(dialog(wrapper).text()).toContain('Delete the closure of Sat 14 Nov 2026?')
    })

    // /planning/ui/schedule-settings/delete-closure
    it('Delete deletes the closure with DELETE', async () => {
      const { calls, mounting } = mountSettings('manager')
      const wrapper = await mounting

      await press(item(wrapper, 'Fête du quartier'), 'Delete the closure')
      await press(dialog(wrapper), 'Delete')

      expect(calls).toContainEqual({
        method: 'DELETE',
        path: `${base}/closures/c-fete`,
        body: undefined,
      })
      expect(dialogs(wrapper)).toHaveLength(0)
      expect(pageText(wrapper)).not.toContain('Fête du quartier')
    })
  })

  describe('Forms', () => {
    // /ui/forms/close
    it('Cancel closes the dialog, changing nothing', async () => {
      const { calls, mounting } = mountSettings('manager')
      const wrapper = await mounting

      await press(wrapper, 'Add a closure')
      await fill(dialog(wrapper), 'From', '2027-02-15')
      await press(dialog(wrapper), 'Cancel')

      expect(dialogs(wrapper)).toHaveLength(0)
      expect(calls.some((c) => c.method === 'POST')).toBe(false)
    })

    // /ui/forms/close
    it('the close button closes the dialog, changing nothing', async () => {
      const { calls, mounting } = mountSettings('manager')
      const wrapper = await mounting

      await press(wrapper, 'Add a closure')
      await fill(dialog(wrapper), 'From', '2027-02-15')
      await press(dialog(wrapper), 'Close')

      expect(dialogs(wrapper)).toHaveLength(0)
      expect(calls.some((c) => c.method === 'POST')).toBe(false)
    })

    // /ui/forms/close
    it('Escape closes the dialog, changing nothing', async () => {
      const { calls, mounting } = mountSettings('manager')
      const wrapper = await mounting

      await press(wrapper, 'Add a closure')
      await fill(dialog(wrapper), 'From', '2027-02-15')
      await pressEscape(wrapper, dialog(wrapper))

      expect(dialogs(wrapper)).toHaveLength(0)
      expect(calls.some((c) => c.method === 'POST')).toBe(false)
    })

    // /ui/forms/dialog
    it('a dialog opened again starts afresh', async () => {
      const { mounting } = mountSettings('manager')
      const wrapper = await mounting

      await press(wrapper, 'Add a closure')
      await fill(dialog(wrapper), 'Label', "Vacances d'hiver")
      await press(dialog(wrapper), 'Cancel')
      await press(wrapper, 'Add a closure')

      expect((field(dialog(wrapper), 'Label').element as HTMLInputElement).value).toBe('')
    })
  })

  describe('planning period, as a manager', () => {
    // /planning/ui/schedule-settings/edit-period
    it('"Edit the period" opens the dialog "Planning period"', async () => {
      const { mounting } = mountSettings('manager')
      const wrapper = await mounting

      await press(wrapper, 'Edit the period')

      const open = dialog(wrapper)
      expect(titleOf(open)).toBe('Planning period')
      expect(showsField(open, 'From')).toBe(true)
      expect(showsField(open, 'To')).toBe(true)
      expect(showsControl(open, 'Save')).toBe(true)
    })

    // /planning/ui/schedule-settings/edit-period
    it('sets the planning period with PUT and closes the dialog', async () => {
      const { calls, mounting } = mountSettings('manager', null)
      const wrapper = await mounting

      await press(wrapper, 'Edit the period')
      await fill(dialog(wrapper), 'From', '2026-11-30')
      await fill(dialog(wrapper), 'To', '2026-12-20')
      await press(dialog(wrapper), 'Save')

      expect(calls).toContainEqual({
        method: 'PUT',
        path: `${base}/planning-period`,
        body: { first: '2026-11-30', last: '2026-12-20' },
      })
      expect(dialogs(wrapper)).toHaveLength(0)
      expect(pageText(wrapper)).toContain('Mon 30 Nov 2026 – Sun 20 Dec 2026')
    })

    // /planning/ui/schedule-settings/clear-period
    it('offers its delete icon only when a period is set', async () => {
      const withPeriod = await mountSettings('manager').mounting
      expect(hasControl(withPeriod, 'Clear the period')).toBe(true)
      withPeriod.unmount()

      const without = await mountSettings('manager', null).mounting
      expect(hasControl(without, 'Clear the period')).toBe(false)
      expect(hasControl(without, 'Edit the period')).toBe(true)
    })

    // /planning/ui/schedule-settings/clear-period
    it('its delete icon asks "Clear the planning period?"', async () => {
      const { calls, mounting } = mountSettings('manager')
      const wrapper = await mounting

      await press(wrapper, 'Clear the period')

      expect(dialog(wrapper).text()).toContain('Clear the planning period?')
      expect(calls.some((c) => c.method === 'DELETE')).toBe(false)
    })

    // /planning/ui/schedule-settings/clear-period
    it('Clear clears the planning period with DELETE', async () => {
      const { calls, mounting } = mountSettings('manager')
      const wrapper = await mounting

      await press(wrapper, 'Clear the period')
      await press(dialog(wrapper), 'Clear')

      expect(calls).toContainEqual({
        method: 'DELETE',
        path: `${base}/planning-period`,
        body: undefined,
      })
      expect(dialogs(wrapper)).toHaveLength(0)
      const text = pageText(wrapper)
      expect(text.slice(text.indexOf('Planning period'), text.indexOf('Closures'))).toContain(
        'None',
      )
    })
  })

  describe('planning period, as a volunteer', () => {
    // /planning/ui/schedule-settings/volunteer /planning/ui/schedule-settings/period
    it('shows the period, without its icons', async () => {
      const { mounting } = mountSettings('volunteer')
      const wrapper = await mounting

      expect(pageText(wrapper)).toContain('Planning period')
      expect(pageText(wrapper)).toContain('Mon 2 Nov 2026 – Wed 25 Nov 2026')
      expect(hasControl(wrapper, 'Edit the period')).toBe(false)
      expect(hasControl(wrapper, 'Clear the period')).toBe(false)
    })

    // /planning/ui/schedule-settings/period
    it('shows "None" when there is no period', async () => {
      const { mounting } = mountSettings('volunteer', null)
      const wrapper = await mounting

      expect(pageText(wrapper)).toContain('None')
    })
  })

  // /planning/ui/schedule-settings/volunteer /ui/forms/managers
  it('a volunteer sees the lists, without the add buttons and the delete icons', async () => {
    const { mounting } = mountSettings('volunteer')
    const wrapper = await mounting

    expect(item(wrapper, 'Thursday').text()).toContain('10:00–13:00')
    expect(item(wrapper, 'Fête du quartier').exists()).toBe(true)
    expect(hasControl(wrapper, 'Delete the slot')).toBe(false)
    expect(hasControl(wrapper, 'Delete the closure')).toBe(false)
    expect(hasControl(wrapper, 'Add a slot')).toBe(false)
    expect(hasControl(wrapper, 'Add a closure')).toBe(false)
  })

  // /planning/ui/schedule-settings/volunteer
  it('a volunteer sees no edit icons on slots and closures', async () => {
    const { mounting } = mountSettings('volunteer')
    const wrapper = await mounting

    expect(hasControl(wrapper, 'Edit the slot')).toBe(false)
    expect(hasControl(wrapper, 'Edit the closure')).toBe(false)
  })

  // Not in the specification: no preference selector on the slots.
  it.each(['manager', 'volunteer'] as const)(
    'a %s sees no preference selector on the slots',
    async (role) => {
      const { mounting } = mountSettings(role)
      const wrapper = await mounting

      expect(item(wrapper, 'Thursday').find('select').exists()).toBe(false)
      expect(pageText(wrapper)).not.toContain('My preference')
    },
  )

  describe("Members' preferences", () => {
    const set: Preference[] = [
      { user_id: 'u-alice', slot_id: 's-thu', value: 'preferred' },
      { user_id: 'u-bruno', slot_id: 's-thu', value: 'possible' },
      { user_id: 'u-bruno', slot_id: 's-sat', value: 'unavailable' },
      { user_id: 'u-chloe', slot_id: 's-sat', value: 'preferred' },
    ]

    // /planning/ui/schedule-settings/preferences
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

    // design.md
    it('each cell is marked with its value', async () => {
      const { mounting } = mountSettings('manager', null, set)
      const grid = memberPreferences(await mounting)

      expect(preferenceOf(grid.cell('Bruno', 0))).toBe('possible')
      expect(preferenceOf(grid.cell('Bruno', 1))).toBe('unavailable')
      expect(preferenceOf(grid.cell('Chloé', 0))).toBeNull()
    })

    // /planning/ui/schedule-settings/set-preference
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

    // /planning/ui/schedule-settings/set-preference
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

    // /planning/ui/schedule-settings/preferences
    it('in French, "Préférences des membres"', async () => {
      localStorage.setItem('gilda.locale', 'fr')
      const { mounting } = mountSettings('manager', null, set)

      expect(pageText(await mounting)).toContain('Préférences des membres')
    })

    // /planning/ui/schedule-settings/preferences
    it('is not shown to a volunteer', async () => {
      const { mounting } = mountSettings('volunteer', null, set)
      const wrapper = await mounting

      expect(pageText(wrapper)).toContain('Thursday')
      expect(pageText(wrapper)).not.toContain("Members' preferences")
      expect(wrapper.find('table').exists()).toBe(false)
    })
  })
})
