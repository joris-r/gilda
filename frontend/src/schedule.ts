import type { OccurrenceRegistration, Schedule } from './api'
import { addDays, formatDate, shortClock, shortDay } from './dates'

/** An occurrence, or an obsolete registration placed like one. */
export interface Item {
  key: string
  date: string
  start: string
  end: string
  registration: OccurrenceRegistration | null
  obsolete: boolean
  lane: number
  lanes: number
}

export function dayLabel(date: string, locale: string) {
  return formatDate(date, locale, shortDay)
}

export function times(item: Item) {
  return `${shortClock(item.start)}–${shortClock(item.end)}`
}

/** What the user may do on `item`, whatever its date. */
export function actions(item: Item, userId: string | undefined, isManager: boolean) {
  const r = item.registration
  const live = r !== null && r.status !== 'cancelled'
  const mine = live && r.user_id === userId
  return {
    signUp: !live && !item.obsolete,
    propose: !live && !item.obsolete && isManager,
    confirm: live && (mine || isManager) && r.status === 'proposed' && !item.obsolete,
    cancel: live && (mine || isManager),
  }
}

export type Actions = ReturnType<typeof actions>

/** The weeks the Schedule shows on opening, and how many "More weeks" adds. */
export const MORE_WEEKS = 4

/** The number of weeks from `from`, a Monday, to `to`, a Sunday. */
export function weeksBetween(from: string, to: string) {
  let count = 1
  while (addDays(from, 7 * count - 1) < to) count++
  return count
}

/** `schedule` followed by `added`, the weeks right after it. */
export function appendSchedule(schedule: Schedule, added: Schedule): Schedule {
  const known = new Set(schedule.closures.map((c) => c.id))
  return {
    from: schedule.from,
    to: added.to,
    occurrences: [...schedule.occurrences, ...added.occurrences],
    obsolete: [...schedule.obsolete, ...added.obsolete],
    closures: [...schedule.closures, ...added.closures.filter((c) => !known.has(c.id))],
  }
}
