import { ref } from 'vue'
import { ApiError, getAssociationBySlug, type Association } from './api'
import { useLocation } from './location'

/**
 * Reads the association of a screen from its slug. Once read, `id` is what the API takes;
 * `unknown` tells that no association of the user has this slug.
 */
export function useAssociationBySlug(slug: () => string) {
  const location = useLocation()
  const id = ref('')
  const unknown = ref(false)

  async function read(): Promise<Association | undefined> {
    unknown.value = false
    try {
      const found = await getAssociationBySlug(slug())
      id.value = found.id
      return found
    } catch (e) {
      if (!(e instanceof ApiError && e.status === 404)) throw e
      unknown.value = true
      location.value = {}
      return undefined
    }
  }

  return { id, unknown, read }
}
