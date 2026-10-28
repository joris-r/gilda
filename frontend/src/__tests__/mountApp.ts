import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory } from 'vue-router'
import App from '../App.vue'
import { createGildaI18n } from '../i18n'
import { createGildaRouter } from '../router'

export async function mountApp(path = '/') {
  const router = createGildaRouter(createMemoryHistory())
  await router.push(path)
  await router.isReady()
  const wrapper = mount(App, { global: { plugins: [router, createGildaI18n()] } })
  await flushPromises()
  return wrapper
}

export function pageText(wrapper: { text(): string }): string {
  return wrapper.text().replace(/\s+/g, ' ')
}
