import type { Weekday } from './api'

/** Dates are local calendar days, written as "YYYY-MM-DD" like the API's. */

export const WEEKDAYS: Weekday[] = [
  'monday',
  'tuesday',
  'wednesday',
  'thursday',
  'friday',
  'saturday',
  'sunday',
]

const TAGS: Record<string, string> = { en: 'en-GB', fr: 'fr-FR' }

export function toIso(day: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${day.getFullYear()}-${pad(day.getMonth() + 1)}-${pad(day.getDate())}`
}

export function fromIso(iso: string): Date {
  const [year, month, day] = iso.split('-').map(Number)
  return new Date(year!, month! - 1, day!)
}

/** Today's date in the given IANA timezone. */
export function today(timeZone: string): string {
  // The en-CA locale writes dates as "YYYY-MM-DD".
  return new Intl.DateTimeFormat('en-CA', { timeZone }).format(new Date())
}

export function addDays(iso: string, days: number): string {
  const day = fromIso(iso)
  day.setDate(day.getDate() + days)
  return toIso(day)
}

/** 0 for Monday to 6 for Sunday. */
export function weekdayIndex(iso: string): number {
  return (fromIso(iso).getDay() + 6) % 7
}

export function mondayOf(iso: string): string {
  return addDays(iso, -weekdayIndex(iso))
}

export function isoWeek(iso: string): number {
  const thursday = fromIso(addDays(iso, 3 - weekdayIndex(iso)))
  const firstOfYear = new Date(thursday.getFullYear(), 0, 1)
  // Rounded first: a daylight saving change makes a day 23 or 25 hours long.
  const days = Math.round((thursday.getTime() - firstOfYear.getTime()) / 86_400_000)
  return 1 + Math.floor(days / 7)
}

/** Formats a date as its parts joined by spaces, e.g. "Thu 5 Nov" or "jeu. 5 nov.". */
export function formatDate(iso: string, locale: string, options: Intl.DateTimeFormatOptions) {
  return new Intl.DateTimeFormat(TAGS[locale] ?? locale, options)
    .formatToParts(fromIso(iso))
    .filter((part) => part.type !== 'literal')
    .map((part) => part.value)
    .join(' ')
}

export const shortDay = { weekday: 'short', day: 'numeric', month: 'short' } as const
export const shortDayWithYear = { ...shortDay, year: 'numeric' } as const
export const longDay = { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' } as const

export function minutes(clock: string): number {
  const [hours, mins] = clock.split(':').map(Number)
  return hours! * 60 + mins!
}

/** "10:00" as "10", "10:30" as "10:30". */
export function shortClock(clock: string): string {
  const [hours, mins] = clock.split(':')
  return mins === '00' ? String(Number(hours)) : `${Number(hours)}:${mins}`
}
