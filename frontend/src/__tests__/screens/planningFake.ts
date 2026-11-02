import type { DOMWrapper, VueWrapper } from '@vue/test-utils'
import { flushPromises } from '@vue/test-utils'
import type { Reply, Route } from '../mockApi'
import { garden, member } from './fixtures'

const base = `/api/associations/${garden.id}`

export interface Occurrence {
  date: string
  start: string
  end: string
}

export interface Registration extends Occurrence {
  id: string
  user_id: string
  display_name: string
  status: 'proposed' | 'confirmed' | 'cancelled'
}

export interface Closure {
  id: string
  first: string
  last: string
  label: string | null
}

export interface PlanningPeriod {
  first: string
  last: string
}

export interface Slot {
  id: string
  weekday: string
  start: string
  end: string
}

export type PreferenceValue = 'preferred' | 'possible' | 'unavailable'

export interface Preference {
  user_id: string
  slot_id: string
  value: PreferenceValue
}

export interface RegistrationCount {
  user_id: string
  count: number
}

const sameOccurrence = (a: Occurrence, b: Occurrence) =>
  a.date === b.date && a.start === b.start && a.end === b.end

/**
 * A small in-memory backend for the planning endpoints, so that a screen may
 * either use the replies of its requests or load the schedule again.
 */
export function planningApi(options: {
  me: string
  role: 'manager' | 'volunteer'
  members: ReturnType<typeof member>[]
  occurrences?: Occurrence[]
  registrations?: Registration[]
  closures?: Closure[]
  slots?: Slot[]
  planningPeriod?: PlanningPeriod | null
  preferences?: Preference[]
  registrationCounts?: RegistrationCount[] | null
}) {
  const occurrences = options.occurrences ?? []
  const registrations = [...(options.registrations ?? [])]
  const closures = [...(options.closures ?? [])]
  const slots = [...(options.slots ?? [])]
  let planningPeriod = options.planningPeriod ?? null
  const preferences = [...(options.preferences ?? [])]
  const scheduleRequests: { from: string | null; to: string | null }[] = []
  let next = 1

  const routes: Record<string, Route> = {
    [`GET ${base}`]: {
      status: 200,
      body: { ...garden, timezone: 'Europe/Paris', role: options.role, members: options.members },
    },
    [`GET ${base}/schedule`]: (_body, _path, url) => {
      const from = url.searchParams.get('from')
      const to = url.searchParams.get('to')
      scheduleRequests.push({ from, to })
      const inRange = (date: string) => (!from || date >= from) && (!to || date <= to)
      const shown = (o: Occurrence) => {
        const all = registrations.filter((r) => sameOccurrence(r, o))
        const live = all.find((r) => r.status !== 'cancelled')
        const reg = live ?? all.filter((r) => r.status === 'cancelled').at(-1)
        return reg
          ? { id: reg.id, user_id: reg.user_id, display_name: reg.display_name, status: reg.status }
          : null
      }
      return {
        status: 200,
        body: {
          occurrences: occurrences
            .filter((o) => inRange(o.date))
            .map((o) => ({ ...o, registration: shown(o) })),
          obsolete: registrations.filter(
            (r) =>
              r.status !== 'cancelled' &&
              inRange(r.date) &&
              !occurrences.some((o) => sameOccurrence(o, r)),
          ),
          closures: closures.filter((c) => (!to || c.first <= to) && (!from || c.last >= from)),
        },
      }
    },
    [`POST ${base}/registrations`]: (body) => {
      const { user_id, date, start, end } = body as Registration
      const user = options.members.find((m) => m.user_id === user_id)!
      const registration: Registration = {
        id: `r-new-${next++}`,
        user_id,
        display_name: user.display_name,
        status: user_id === options.me ? 'confirmed' : 'proposed',
        date,
        start,
        end,
      }
      registrations.push(registration)
      addPatch(registration)
      return { status: 201, body: registration }
    },
    [`GET ${base}/slots`]: () => ({ status: 200, body: slots }),
    [`POST ${base}/slots`]: (body) => {
      const slot = { id: `s-new-${next++}`, ...(body as Omit<Slot, 'id'>) }
      slots.push(slot)
      addPut('slots', slots, slot.id)
      addDelete('slots', slots, slot.id)
      addPreferenceRoutes(slot)
      return { status: 201, body: slot }
    },
    [`GET ${base}/closures`]: () => ({ status: 200, body: closures }),
    [`POST ${base}/closures`]: (body) => {
      const given = body as Partial<Closure>
      const closure = {
        id: `c-new-${next++}`,
        first: given.first!,
        last: given.last!,
        label: given.label ?? null,
      }
      closures.push(closure)
      addPut('closures', closures, closure.id)
      addDelete('closures', closures, closure.id)
      return { status: 201, body: closure }
    },
    [`GET ${base}/planning-period`]: () => ({ status: 200, body: planningPeriod }),
    [`PUT ${base}/planning-period`]: (body) => {
      planningPeriod = body as PlanningPeriod
      return { status: 200, body: planningPeriod }
    },
    [`DELETE ${base}/planning-period`]: () => {
      planningPeriod = null
      return { status: 204 }
    },
    [`GET ${base}/preferences`]: () => ({
      status: 200,
      body: preferences.filter((p) => options.role === 'manager' || p.user_id === options.me),
    }),
    [`GET ${base}/registration-counts`]: () =>
      options.role === 'manager'
        ? { status: 200, body: planningPeriod ? (options.registrationCounts ?? []) : null }
        : { status: 403, body: { error: 'Managers only' } },
  }

  function addPreferenceRoutes(slot: Slot) {
    for (const m of options.members) {
      const at = `${base}/preferences/${slot.id}/${m.user_id}`
      const allowed = () => options.role === 'manager' || m.user_id === options.me
      const index = () =>
        preferences.findIndex((p) => p.slot_id === slot.id && p.user_id === m.user_id)
      routes[`PUT ${at}`] = (body): Reply => {
        if (!allowed()) return { status: 403, body: { error: 'Forbidden' } }
        const preference = {
          user_id: m.user_id,
          slot_id: slot.id,
          value: (body as { value: PreferenceValue }).value,
        }
        if (index() >= 0) preferences.splice(index(), 1)
        preferences.push(preference)
        return { status: 200, body: preference }
      }
      routes[`DELETE ${at}`] = (): Reply => {
        if (!allowed()) return { status: 403, body: { error: 'Forbidden' } }
        if (index() >= 0) preferences.splice(index(), 1)
        return { status: 204 }
      }
    }
  }

  function addPatch(registration: Registration) {
    routes[`PATCH ${base}/registrations/${registration.id}`] = (body): Reply => {
      registration.status = (body as { status: Registration['status'] }).status
      return { status: 200, body: registration }
    }
  }

  function addPut(kind: string, list: { id: string }[], id: string) {
    routes[`PUT ${base}/${kind}/${id}`] = (body): Reply => {
      const edited = { id, ...(kind === 'closures' ? { label: null } : {}), ...(body as object) }
      list.splice(
        list.findIndex((x) => x.id === id),
        1,
        edited,
      )
      return { status: 200, body: edited }
    }
  }

  function addDelete(kind: string, list: { id: string }[], id: string) {
    routes[`DELETE ${base}/${kind}/${id}`] = (): Reply => {
      list.splice(
        list.findIndex((x) => x.id === id),
        1,
      )
      return { status: 204 }
    }
  }

  registrations.forEach(addPatch)
  slots.forEach((s) => addPut('slots', slots, s.id))
  slots.forEach((s) => addDelete('slots', slots, s.id))
  slots.forEach(addPreferenceRoutes)
  closures.forEach((c) => addPut('closures', closures, c.id))
  closures.forEach((c) => addDelete('closures', closures, c.id))

  return { routes, scheduleRequests, preferences }
}

type Wrapper = VueWrapper | DOMWrapper<Element>

/** The group of a day of the schedule, labelled like "Thu 5 Nov". */
export function day(wrapper: Wrapper, label: string): DOMWrapper<Element> {
  const group = wrapper.findAll('[role="group"]').find((g) => g.attributes('aria-label') === label)
  if (group === undefined) throw new Error(`No day "${label}"`)
  return group
}

export function hasDay(wrapper: Wrapper, prefix: string): boolean {
  return wrapper
    .findAll('[role="group"]')
    .some((g) => (g.attributes('aria-label') ?? '').startsWith(prefix))
}

/** The occurrence or obsolete registration of a day, by its times as shown ("10–13"). */
export function slotItem(wrapper: Wrapper, dayLabel: string, times: string): DOMWrapper<Element> {
  const element = day(wrapper, dayLabel)
    .findAll('li')
    .find((li) => li.text().includes(times))
  if (element === undefined) throw new Error(`No item ${times} on "${dayLabel}"`)
  return element
}

/** Clicks an item of the schedule, to open its menu. */
export async function open(element: DOMWrapper<Element>) {
  const button = element.find('button')
  await (button.exists() ? button : element).trigger('click')
  await flushPromises()
}

const PREFERENCE_VALUES: PreferenceValue[] = ['preferred', 'possible', 'unavailable']

/** The preference an element is marked with, by its class `preference-<value>`; null when none. */
export function preferenceOf(element: DOMWrapper<Element>): PreferenceValue | null {
  return PREFERENCE_VALUES.find((v) => element.classes().includes(`preference-${v}`)) ?? null
}
