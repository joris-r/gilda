import { createApp } from 'vue'
import App from './App.vue'
import { createGildaI18n } from './i18n'
import { createGildaRouter } from './router'

const app = createApp(App)

app.use(createGildaRouter())
app.use(createGildaI18n())

app.mount('#app')
