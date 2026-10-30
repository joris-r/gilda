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

export interface Member {
  user_id: string
  display_name: string
  email: string
  has_account: boolean
  email_verified: boolean
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
  const response = await fetch(path, {
    method,
    headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
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

export function listAssociations() {
  return request<AssociationSummary[]>('GET', '/api/associations')
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

export function deleteSlot(id: string, slotId: string) {
  return request<void>('DELETE', `/api/associations/${id}/slots/${slotId}`)
}

export function listClosures(id: string) {
  return request<Closure[]>('GET', `/api/associations/${id}/closures`)
}

export function addClosure(id: string, first: string, last: string, label: string | null) {
  return request<Closure>('POST', `/api/associations/${id}/closures`, { first, last, label })
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
