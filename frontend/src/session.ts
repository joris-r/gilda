import { inject, provide, ref, type InjectionKey, type Ref } from 'vue'
import type { User } from './api'

export interface Session {
  /** undefined until loaded, null when signed out. */
  user: Ref<User | null | undefined>
}

const key: InjectionKey<Session> = Symbol('session')

export function provideSession(): Session {
  const session: Session = { user: ref(undefined) }
  provide(key, session)
  return session
}

export function useSession(): Session {
  const session = inject(key)
  if (session === undefined) throw new Error('useSession() needs provideSession()')
  return session
}
