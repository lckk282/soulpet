import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import AppIcon from './components/AppIcon.vue'
import './styles.css'

createApp(App)
  .use(createPinia())
  .use(router)
  .component('AppIcon', AppIcon)
  .mount('#app')
