import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import 'element-plus/dist/index.css'
import './ku.css'
import './macos.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import App from './App.vue'
import router from './router'
import api from './api'
import { initTheme } from './theme'
import { initDialogResize } from './utils/resizable'
import { initColResize } from './utils/colResize'

initTheme()
initDialogResize()
initColResize()

const app = createApp(App)
for (const [key, comp] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, comp)
}
app.use(ElementPlus, { locale: zhCn })
app.use(router)
app.config.globalProperties.$api = api
app.mount('#app')
