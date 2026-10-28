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

export interface Slot {
  id: string
  weekday: string
  start: string
  end: string
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
}) {
  const occurrences = options.occurrences ?? []
  const registrations = [...(options.registrations ?? [])]
  const closures = [...(options.closures ?? [])]
  const slots = [...(options.slots ?? [])]
  const scheduleRequests: { from: string | null; to: string | null }[] = []
  let next = 1

  const routes: Record<string, Route> = {
    [`GET ${base}`]: {
      status: 200,
      body: { ...garden, role: options.role, members: options.members },
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
      addDelete('slots', slots, slot.id)
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
      addDelete('closures', closures, closure.id)
      return { status: 201, body: closure }
    },
  }

  function addPatch(registration: Registration) {
    routes[`PATCH ${base}/registrations/${registration.id}`] = (body): Reply => {
      registration.status = (body as { status: Registration['status'] }).status
      return { status: 200, body: registration }
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
  slots.forEach((s) => addDelete('slots', slots, s.id))
  closures.forEach((c) => addDelete('closures', closures, c.id))

  return { routes, scheduleRequests }
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
