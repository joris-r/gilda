import { ApiError } from './api'

const MAX_LENGTH = 50

/** R35: what Association identifier shows for a name, until the user edits it. */
export function slugFromName(name: string): string {
  return name
    .normalize('NFD')
    .replace(/\p{M}/gu, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, MAX_LENGTH)
    .replace(/-+$/, '')
}

/** The i18n key of the message for a refused slug. */
export function slugErrorKey(e: unknown): string {
  if (e instanceof ApiError && e.status === 400) return 'association.identifierInvalid'
  if (e instanceof ApiError && e.status === 409) return 'association.identifierTaken'
  return 'error'
}
