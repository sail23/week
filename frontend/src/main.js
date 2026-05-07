import { createApp } from 'vue'
import { marked } from 'marked'
import App from './App.vue'
import './style.css'

marked.setOptions({
  gfm: true,
  breaks: true,
})

createApp(App).mount('#app')
