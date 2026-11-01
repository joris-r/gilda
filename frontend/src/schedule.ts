import type { OccurrenceRegistration } from './api'
import { formatDate, shortClock, shortDay } from './dates'

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
