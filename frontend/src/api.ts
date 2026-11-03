import { currentLocale } from './i18n'

export type Role = 'manager' | 'volunteer'

export interface User {
  id: string
  display_name: string
  email: string
}

export interface AssociationSummary {
  id: string
  name: string
  role: Role
}

/** An association as My associations shows it. */
export interface HomeAssociation extends AssociationSummary {
  upcoming: Registration[]
  obsolete: Registration[]
  planning_period: PlanningPeriodSummary | null
}

export interface Member {
  user_id: string
  display_name: string
  email: string
  has_account: boolean
  email_verified: boolean
  access_link: boolean
  role: Role
}

export interface Association extends AssociationSummary {
  timezone: string
  members: Member[]
}

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message)
  }
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = { 'Accept-Language': currentLocale() }
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  const response = await fetch(path, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  if (!response.ok) {
    const error = (await response.json().catch(() => ({}))) as { error?: string }
    throw new ApiError(response.status, error.error ?? response.statusText)
  }
  return (response.status === 204 ? undefined : await response.json()) as T
}

/** Resolves to undefined when signed out. */
export async function getSession(): Promise<User | undefined> {
  try {
    return await request<User>('GET', '/api/session')
  } catch {
    return undefined
  }
}

export function signIn(email: string, password: string) {
  return request<User>('POST', '/api/session', { email, password })
}

export function signOut() {
  return request<void>('DELETE', '/api/session')
}

export function createAccount(display_name: string, email: string, password: string) {
  return request<User>('POST', '/api/accounts', { display_name, email, password })
}

export function verifyEmail(token: string) {
  return request<User>('POST', '/api/accounts/verify', { token })
}

export function resendVerification(email: string) {
  return request<void>('POST', '/api/accounts/verify/resend', { email })
}

export function requestPasswordReset(email: string) {
  return request<void>('POST', '/api/accounts/password-reset', { email })
}

export function resetPassword(token: string, password: string) {
  return request<User>('POST', '/api/accounts/password-reset/confirm', { token, password })
}

export function requestAccessLink(email: string) {
  return request<void>('POST', '/api/access-link', { email })
}

export function signInWithLink(token: string) {
  return request<User>('POST', '/api/session/access-link', { token })
}

export function deleteAccount() {
  return request<void>('DELETE', '/api/accounts/me')
}

export function revokeAccessLink() {
  return request<void>('DELETE', '/api/access-link')
}

export function listAssociations() {
  return request<HomeAssociation[]>('GET', '/api/associations')
}

export function createAssociation(name: string) {
  return request<AssociationSummary>('POST', '/api/associations', { name })
}

export function getAssociation(id: string) {
  return request<Association>('GET', `/api/associations/${id}`)
}

export function addMember(id: string, display_name: string, email: string, role: Role) {
  return request<Member>('POST', `/api/associations/${id}/members`, { display_name, email, role })
}

export function changeRole(id: string, userId: string, role: Role) {
  return request<Member>('PATCH', `/api/associations/${id}/members/${userId}`, { role })
}

export function sendMemberLink(id: string, userId: string) {
  return request<Member>('POST', `/api/associations/${id}/members/${userId}/access-link`)
}

export function removeMember(id: string, userId: string) {
  return request<void>('DELETE', `/api/associations/${id}/members/${userId}`)
}

export function revokeMemberLink(id: string, userId: string) {
  return request<void>('DELETE', `/api/associations/${id}/members/${userId}/access-link`)
}

export type Weekday =
  'monday' | 'tuesday' | 'wednesday' | 'thursday' | 'friday' | 'saturday' | 'sunday'

export type Status = 'proposed' | 'confirmed' | 'cancelled'

export interface Slot {
  id: string
  weekday: Weekday
  start: string
  end: string
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

export interface PlanningPeriodSummary extends PlanningPeriod {
  registrations: number
}

export interface OccurrenceRegistration {
  id: string
  user_id: string
  display_name: string
  status: Status
}

export interface Registration extends OccurrenceRegistration {
  date: string
  start: string
  end: string
}

export interface Occurrence {
  date: string
  start: string
  end: string
  registration: OccurrenceRegistration | null
}

export interface Schedule {
  occurrences: Occurrence[]
  obsolete: Registration[]
  closures: Closure[]
}

export function listSlots(id: string) {
  return request<Slot[]>('GET', `/api/associations/${id}/slots`)
}

export function addSlot(id: string, weekday: Weekday, start: string, end: string) {
  return request<Slot>('POST', `/api/associations/${id}/slots`, { weekday, start, end })
}

export function editSlot(id: string, slotId: string, weekday: Weekday, start: string, end: string) {
  return request<Slot>('PUT', `/api/associations/${id}/slots/${slotId}`, { weekday, start, end })
}

export function deleteSlot(id: string, slotId: string) {
  return request<void>('DELETE', `/api/associations/${id}/slots/${slotId}`)
}

export function listClosures(id: string) {
  return request<Closure[]>('GET', `/api/associations/${id}/closures`)
}

export function addClosure(id: string, first: string, last: string, label: string | null) {
  return request<Closure>('POST', `/api/associations/${id}/closures`, { first, last, label })
}

export function editClosure(
  id: string,
  closureId: string,
  first: string,
  last: string,
  label: string | null,
) {
  return request<Closure>('PUT', `/api/associations/${id}/closures/${closureId}`, {
    first,
    last,
    label,
  })
}

export function deleteClosure(id: string, closureId: string) {
  return request<void>('DELETE', `/api/associations/${id}/closures/${closureId}`)
}

export function getPlanningPeriod(id: string) {
  return request<PlanningPeriod | null>('GET', `/api/associations/${id}/planning-period`)
}

export function setPlanningPeriod(id: string, first: string, last: string) {
  return request<PlanningPeriod>('PUT', `/api/associations/${id}/planning-period`, { first, last })
}

export function clearPlanningPeriod(id: string) {
  return request<void>('DELETE', `/api/associations/${id}/planning-period`)
}

export function getSchedule(id: string, from: string, to: string) {
  const query = new URLSearchParams({ from, to })
  return request<Schedule>('GET', `/api/associations/${id}/schedule?${query}`)
}

export function register(id: string, userId: string, date: string, start: string, end: string) {
  return request<Registration>('POST', `/api/associations/${id}/registrations`, {
    user_id: userId,
    date,
    start,
    end,
  })
}

export function setRegistrationStatus(id: string, registrationId: string, status: Status) {
  return request<Registration>('PATCH', `/api/associations/${id}/registrations/${registrationId}`, {
    status,
  })
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

export function listPreferences(id: string) {
  return request<Preference[]>('GET', `/api/associations/${id}/preferences`)
}

export function setPreference(id: string, slotId: string, userId: string, value: PreferenceValue) {
  return request<Preference>('PUT', `/api/associations/${id}/preferences/${slotId}/${userId}`, {
    value,
  })
}

export function deletePreference(id: string, slotId: string, userId: string) {
  return request<void>('DELETE', `/api/associations/${id}/preferences/${slotId}/${userId}`)
}

export interface Absence {
  id: string
  first: string
  last: string
}

export function listAbsences(id: string) {
  return request<Absence[]>('GET', `/api/associations/${id}/absences`)
}

export function addAbsence(id: string, first: string, last: string) {
  return request<Absence>('POST', `/api/associations/${id}/absences`, { first, last })
}

export function editAbsence(id: string, absenceId: string, first: string, last: string) {
  return request<Absence>('PUT', `/api/associations/${id}/absences/${absenceId}`, { first, last })
}

export function deleteAbsence(id: string, absenceId: string) {
  return request<void>('DELETE', `/api/associations/${id}/absences/${absenceId}`)
}

export interface MemberAbsence extends Absence {
  user_id: string
}

export function listMemberAbsences(id: string) {
  return request<MemberAbsence[]>('GET', `/api/associations/${id}/member-absences`)
}

export interface MemberNote {
  user_id: string
  text: string
}

export function listNotes(id: string) {
  return request<MemberNote[]>('GET', `/api/associations/${id}/notes`)
}

export async function getNote(id: string) {
  return (await request<{ text: string }>('GET', `/api/associations/${id}/note`)).text
}

export async function setNote(id: string, text: string) {
  return (await request<{ text: string }>('PUT', `/api/associations/${id}/note`, { text })).text
}

export function getRegistrationCounts(id: string) {
  return request<RegistrationCount[] | null>('GET', `/api/associations/${id}/registration-counts`)
}
