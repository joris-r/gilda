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
  showsControl,
  showsField,
  titleOf,
} from '../mockApi'
import { garden, member, signedInAsAlice } from './fixtures'
import { planningApi, preferenceOf, type Absence, type Preference, type Slot } from './planningFake'

const path = `/association/${garden.slug}/availability`
const base = `/api/associations/${garden.id}`

const thuAndSat: Slot[] = [
  { id: 's-thu', weekday: 'thursday', start: '10:00', end: '13:00' },
  { id: 's-sat', weekday: 'saturday', start: '10:00', end: '13:00' },
]

const holidays: Absence = { id: 'ab-holidays', first: '2026-11-09', last: '2026-11-15' }

function mountAvailability(
  options: {
    role?: 'manager' | 'volunteer'
    slots?: Slot[]
    preferences?: Preference[]
    absences?: Absence[]
    note?: string
  } = {},
) {
  const role = options.role ?? 'volunteer'
  const api = planningApi({
    me: 'u-alice',
    role,
    members: [member('u-alice', 'Alice', role), member('u-bruno', 'Bruno', 'volunteer')],
    slots: options.slots ?? thuAndSat,
    preferences: options.preferences ?? [],
    absences: options.absences ?? [holidays],
    note: options.note ?? '',
  })
  const calls = mockApi({ 'GET /api/session': signedInAsAlice, ...api.routes })
  return { calls, mounting: mountApp(path) }
}

/** The preference selector of the slot listed with `weekday`. */
function preferenceSelector(wrapper: VueWrapper, weekday: string) {
  return item(wrapper, weekday).find('select')
}

/** The selected option's text of a selector. */
function shown(select: DOMWrapper<Element>) {
  const element = select.element as HTMLSelectElement
  return element.options[element.selectedIndex]?.text.trim()
}

/** The section whose heading is `title`. */
function section(wrapper: VueWrapper, title: string): DOMWrapper<Element> {
  const heading = wrapper.findAll('h1, h2, h3').find((h) => h.text().trim() === title)
  if (heading === undefined) throw new Error(`No section "${title}"`)
  const element = heading.element.closest('section')
  if (element === null) throw new Error(`Section "${title}" is not in a <section>`)
  return wrapper.findAll('section').find((s) => s.element === element)!
}

beforeEach(() => {
  localStorage.clear()
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(new Date(2026, 10, 2, 10, 0))
})

afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

describe('My availability', () => {
  // /core/ui/header/location
  it('the header shows the association name, then My availability', async () => {
    const text = header(await mountAvailability().mounting).text()

    expect(text).toContain(garden.name)
    expect(text.indexOf('My availability')).toBeGreaterThan(text.indexOf(garden.name))
  })

  // /planning/ui/my-availability/french
  it('in French, the screen is "Mes disponibilités"', async () => {
    localStorage.setItem('gilda.locale', 'fr')

    expect(header(await mountAvailability().mounting).text()).toContain('Mes disponibilités')
  })

  // /planning/ui/my-availability/preferences /planning/ui/my-availability/absences /planning/ui/my-availability/note
  it('shows My preferences, then Absences, then Note for the managers', async () => {
    const wrapper = await mountAvailability().mounting

    const sections = wrapper
      .findAll('h1, h2, h3')
      .map((h) => h.text().trim())
      .filter((text) => ['My preferences', 'Absences', 'Note for the managers'].includes(text))
    expect(sections).toEqual(['My preferences', 'Absences', 'Note for the managers'])
  })

  // /planning/ui/my-availability/french
  it('in French, the sections and "Ajouter une absence"', async () => {
    localStorage.setItem('gilda.locale', 'fr')
    const wrapper = await mountAvailability().mounting

    const text = pageText(wrapper)
    expect(text).toContain('Mes préférences')
    expect(text).toContain('Absences')
    expect(text).toContain('Note pour les responsables')
    expect(hasControl(wrapper, 'Ajouter une absence')).toBe(true)
  })

  describe('My preferences', () => {
    // /planning/ui/my-availability/preferences /planning/ui/my-availability/own
    it.each(['manager', 'volunteer'] as const)(
      'a %s sees each slot, with their own preference, "—" when none',
      async (role) => {
        const wrapper = await mountAvailability({
          role,
          preferences: [
            { user_id: 'u-alice', slot_id: 's-thu', value: 'preferred' },
            { user_id: 'u-bruno', slot_id: 's-sat', value: 'unavailable' },
          ],
        }).mounting

        expect(item(wrapper, 'Thursday').text()).toContain('10:00–13:00')
        expect(shown(preferenceSelector(wrapper, 'Thursday'))).toBe('Preferred')
        expect(shown(preferenceSelector(wrapper, 'Saturday'))).toBe('—')
      },
    )

    // /planning/ui/my-availability/own
    it("a manager sees no other member's preferences", async () => {
      const wrapper = await mountAvailability({
        role: 'manager',
        preferences: [{ user_id: 'u-bruno', slot_id: 's-thu', value: 'unavailable' }],
      }).mounting

      expect(shown(preferenceSelector(wrapper, 'Thursday'))).toBe('—')
      expect(pageText(wrapper)).not.toContain('Bruno')
    })

    // /planning/ui/my-availability/preferences
    it('offers "—", Preferred, Possible and Unavailable', async () => {
      const wrapper = await mountAvailability().mounting

      const options = preferenceSelector(wrapper, 'Thursday')
        .findAll('option')
        .map((o) => o.text().trim())
      expect(options).toEqual(['—', 'Preferred', 'Possible', 'Unavailable'])
    })

    // /planning/ui/my-availability/set
    it('choosing a value saves it at once with PUT', async () => {
      const { calls, mounting } = mountAvailability()
      const wrapper = await mounting

      await preferenceSelector(wrapper, 'Thursday').setValue('possible')
      await flushPromises()

      expect(calls).toContainEqual({
        method: 'PUT',
        path: `${base}/preferences/s-thu/u-alice`,
        body: { value: 'possible' },
      })
    })

    // /planning/ui/my-availability/set
    it('choosing "—" deletes it with DELETE', async () => {
      const { calls, mounting } = mountAvailability({
        preferences: [{ user_id: 'u-alice', slot_id: 's-thu', value: 'preferred' }],
      })
      const wrapper = await mounting

      const select = preferenceSelector(wrapper, 'Thursday')
      const none = select.findAll('option').find((o) => o.text().trim() === '—')!
      await select.setValue((none.element as HTMLOptionElement).value)
      await flushPromises()

      expect(calls).toContainEqual({
        method: 'DELETE',
        path: `${base}/preferences/s-thu/u-alice`,
        body: undefined,
      })
    })

    // design.md
    it('the selector is marked with its value, unmarked for "—"', async () => {
      const wrapper = await mountAvailability({
        preferences: [{ user_id: 'u-alice', slot_id: 's-thu', value: 'unavailable' }],
      }).mounting

      expect(preferenceOf(preferenceSelector(wrapper, 'Thursday'))).toBe('unavailable')
      expect(preferenceOf(preferenceSelector(wrapper, 'Saturday'))).toBeNull()

      await preferenceSelector(wrapper, 'Saturday').setValue('preferred')
      await flushPromises()

      expect(preferenceOf(preferenceSelector(wrapper, 'Saturday'))).toBe('preferred')
    })

    // /planning/ui/my-availability/french
    it('in French, the values', async () => {
      localStorage.setItem('gilda.locale', 'fr')
      const wrapper = await mountAvailability().mounting

      const options = wrapper
        .find('li select')
        .findAll('option')
        .map((o) => o.text().trim())
      expect(options).toEqual(['—', 'Préféré', 'Possible', 'Indisponible'])
    })

    // /planning/ui/my-availability/none
    it('with no slot, shows "None"', async () => {
      const wrapper = await mountAvailability({ slots: [] }).mounting

      expect(section(wrapper, 'My preferences').text()).toContain('None')
    })
  })

  describe('Absences', () => {
    // /planning/ui/my-availability/absences
    it('lists the absences, with their dates', async () => {
      const wrapper = await mountAvailability().mounting

      expect(section(wrapper, 'Absences').text()).toContain('Mon 9 Nov 2026 – Sun 15 Nov 2026')
    })

    // /planning/ui/my-availability/none
    it('with no absence, shows "None"', async () => {
      const wrapper = await mountAvailability({ absences: [] }).mounting

      expect(section(wrapper, 'Absences').text()).toContain('None')
    })

    // /planning/ui/my-availability/absences
    it('lists those ending today on; earlier ones do not show', async () => {
      const wrapper = await mountAvailability({
        absences: [
          { id: 'ab-past', first: '2026-10-19', last: '2026-11-01' },
          { id: 'ab-today', first: '2026-10-26', last: '2026-11-02' },
          holidays,
        ],
      }).mounting

      const text = section(wrapper, 'Absences').text()
      expect(text).not.toContain('Mon 19 Oct 2026')
      expect(text).toContain('Mon 26 Oct 2026 – Mon 2 Nov 2026')
      expect(text).toContain('Mon 9 Nov 2026 – Sun 15 Nov 2026')
    })

    // /planning/ui/my-availability/own
    it.each(['manager', 'volunteer'] as const)(
      'a %s sees "Add an absence" and the edit and delete icons',
      async (role) => {
        const wrapper = await mountAvailability({ role }).mounting

        expect(showsControl(wrapper, 'Add an absence')).toBe(true)
        expect(hasControl(item(wrapper, 'Mon 9 Nov 2026'), 'Edit the absence')).toBe(true)
        expect(hasControl(item(wrapper, 'Mon 9 Nov 2026'), 'Delete the absence')).toBe(true)
      },
    )

    // /planning/ui/my-availability/add-absence
    it('"Add an absence" opens the dialog "Add an absence"', async () => {
      const wrapper = await mountAvailability().mounting

      await press(wrapper, 'Add an absence')

      const open = dialog(wrapper)
      expect(titleOf(open)).toBe('Add an absence')
      expect(showsField(open, 'From')).toBe(true)
      expect(showsField(open, 'To')).toBe(true)
      expect(showsControl(open, 'Add absence')).toBe(true)
    })

    // /planning/ui/my-availability/add-absence
    it('adds an absence with POST and closes the dialog', async () => {
      const { calls, mounting } = mountAvailability({ absences: [] })
      const wrapper = await mounting

      await press(wrapper, 'Add an absence')
      await fill(dialog(wrapper), 'From', '2026-12-21')
      await fill(dialog(wrapper), 'To', '2027-01-03')
      await press(dialog(wrapper), 'Add absence')

      expect(calls).toContainEqual({
        method: 'POST',
        path: `${base}/absences`,
        body: { first: '2026-12-21', last: '2027-01-03' },
      })
      expect(dialogs(wrapper)).toHaveLength(0)
      expect(section(wrapper, 'Absences').text()).toContain('Mon 21 Dec 2026 – Sun 3 Jan 2027')
    })

    // /planning/ui/my-availability/invalid
    it('an absence refused for its order keeps the dialog open, with its message', async () => {
      const { mounting } = mountAvailability({ absences: [] })
      const wrapper = await mounting
      mockApi({
        'GET /api/session': signedInAsAlice,
        [`POST ${base}/absences`]: { status: 400, body: { error: 'Order' } },
      })

      await press(wrapper, 'Add an absence')
      await fill(dialog(wrapper), 'From', '2027-01-03')
      await fill(dialog(wrapper), 'To', '2026-12-21')
      await press(dialog(wrapper), 'Add absence')

      expect(dialogs(wrapper)).toHaveLength(1)
      expect(dialog(wrapper).text()).toContain('Check the dates: the start comes before the end.')
    })

    // /planning/ui/my-availability/edit-absence
    it('the edit icon opens "Edit the absence", filled with it, and Save saves it with PUT', async () => {
      const { calls, mounting } = mountAvailability()
      const wrapper = await mounting

      await press(item(wrapper, 'Mon 9 Nov 2026'), 'Edit the absence')

      const open = dialog(wrapper)
      expect(titleOf(open)).toBe('Edit the absence')
      expect((field(open, 'From').element as HTMLInputElement).value).toBe('2026-11-09')
      expect((field(open, 'To').element as HTMLInputElement).value).toBe('2026-11-15')

      await fill(open, 'To', '2026-11-20')
      await press(open, 'Save')

      expect(calls).toContainEqual({
        method: 'PUT',
        path: `${base}/absences/ab-holidays`,
        body: { first: '2026-11-09', last: '2026-11-20' },
      })
      expect(dialogs(wrapper)).toHaveLength(0)
      expect(section(wrapper, 'Absences').text()).toContain('Mon 9 Nov 2026 – Fri 20 Nov 2026')
    })

    // /planning/ui/my-availability/delete-absence
    it('the delete icon asks "Delete the absence of Mon 9 Nov 2026 – Sun 15 Nov 2026?"', async () => {
      const { calls, mounting } = mountAvailability()
      const wrapper = await mounting

      await press(item(wrapper, 'Mon 9 Nov 2026'), 'Delete the absence')

      expect(dialog(wrapper).text()).toContain(
        'Delete the absence of Mon 9 Nov 2026 – Sun 15 Nov 2026?',
      )
      expect(calls.some((c) => c.method === 'DELETE')).toBe(false)
    })

    // /planning/ui/my-availability/delete-absence
    it('Delete deletes the absence with DELETE', async () => {
      const { calls, mounting } = mountAvailability()
      const wrapper = await mounting

      await press(item(wrapper, 'Mon 9 Nov 2026'), 'Delete the absence')
      await press(dialog(wrapper), 'Delete')

      expect(calls).toContainEqual({
        method: 'DELETE',
        path: `${base}/absences/ab-holidays`,
        body: undefined,
      })
      expect(dialogs(wrapper)).toHaveLength(0)
      expect(section(wrapper, 'Absences').text()).not.toContain('Mon 9 Nov 2026')
    })
  })

  describe('Note for the managers', () => {
    // /planning/ui/my-availability/note
    it('shows the note', async () => {
      const wrapper = await mountAvailability({
        note: 'Always group my registrations in pairs.',
      }).mounting

      expect(section(wrapper, 'Note for the managers').text()).toContain(
        'Always group my registrations in pairs.',
      )
    })

    // /planning/ui/my-availability/none
    it('with an empty note, shows "None"', async () => {
      const wrapper = await mountAvailability().mounting

      expect(section(wrapper, 'Note for the managers').text()).toContain('None')
    })

    // /planning/ui/my-availability/edit-note
    it('the edit icon opens "Note for the managers", filled with the note', async () => {
      const wrapper = await mountAvailability({ note: 'Mornings only.' }).mounting

      await press(section(wrapper, 'Note for the managers'), 'Edit the note')

      const open = dialog(wrapper)
      expect(titleOf(open)).toBe('Note for the managers')
      const text = field(open, 'Text')
      expect(text.element.tagName).toBe('TEXTAREA')
      expect((text.element as HTMLTextAreaElement).value).toBe('Mornings only.')
      expect(showsControl(open, 'Save')).toBe(true)
    })

    // /planning/ui/my-availability/edit-note
    it('Save saves the note with PUT and shows it', async () => {
      const { calls, mounting } = mountAvailability()
      const wrapper = await mounting

      await press(section(wrapper, 'Note for the managers'), 'Edit the note')
      await fill(dialog(wrapper), 'Text', 'Always group my registrations\nin pairs.')
      await press(dialog(wrapper), 'Save')

      expect(calls).toContainEqual({
        method: 'PUT',
        path: `${base}/note`,
        body: { text: 'Always group my registrations\nin pairs.' },
      })
      expect(dialogs(wrapper)).toHaveLength(0)
      expect(pageText(section(wrapper, 'Note for the managers'))).toContain(
        'Always group my registrations in pairs.',
      )
    })
  })
})
