import { inject, provide, ref, type InjectionKey, type Ref } from 'vue'

/** Where the user is, shown in the header. Each screen sets it once it knows. */
export interface Location {
  association?: { id: string; name: string }
  /** The i18n key of the screen's name. */
  screen?: string
}

const key: InjectionKey<Ref<Location>> = Symbol('location')

export function provideLocation(): Ref<Location> {
  const location = ref<Location>({})
  provide(key, location)
  return location
}

export function useLocation(): Ref<Location> {
  const location = inject(key)
  if (location === undefined) throw new Error('useLocation() needs provideLocation()')
  return location
}
