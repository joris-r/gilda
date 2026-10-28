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
  role: Role
}

export interface Association extends AssociationSummary {
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
