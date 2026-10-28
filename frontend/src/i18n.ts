import { createI18n } from 'vue-i18n'

export function createGildaI18n() {
  return createI18n({ legacy: false, locale: 'en', messages: { en: {}, fr: {} } })
}
