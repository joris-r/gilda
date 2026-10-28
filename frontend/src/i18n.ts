import { createI18n } from 'vue-i18n'
import en from './locales/en.json'
import fr from './locales/fr.json'

export const LOCALES = ['en', 'fr'] as const
export type Locale = (typeof LOCALES)[number]

const STORAGE_KEY = 'gilda.locale'

export function createGildaI18n() {
  return createI18n<[typeof en], Locale>({
    legacy: false,
    locale: storedLocale() ?? 'en',
    fallbackLocale: 'en',
    messages: { en, fr },
  })
}

export function storeLocale(locale: Locale) {
  try {
    localStorage.setItem(STORAGE_KEY, locale)
  } catch {
    // Storage may be unavailable (private mode): the choice lasts for this visit only.
  }
}

function storedLocale(): Locale | undefined {
  try {
    const value = localStorage.getItem(STORAGE_KEY)
    return LOCALES.find((locale) => locale === value)
  } catch {
    return undefined
  }
}
