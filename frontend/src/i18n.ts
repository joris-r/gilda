import { createI18n } from 'vue-i18n'
import en from './locales/en.json'
import fr from './locales/fr.json'

export const LOCALES = ['en', 'fr'] as const
export type Locale = (typeof LOCALES)[number]

const STORAGE_KEY = 'gilda.locale'

export function createGildaI18n() {
  return createI18n<[typeof en], Locale>({
    legacy: false,
    locale: storedLocale() ?? browserLocale(),
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

/** The browser's most preferred language that Gilda speaks, English otherwise. */
function browserLocale(): Locale {
  const preferred = navigator.languages?.length ? navigator.languages : [navigator.language]
  for (const language of preferred) {
    const code = LOCALES.find((locale) => language?.toLowerCase().split('-')[0] === locale)
    if (code !== undefined) return code
  }
  return 'en'
}
