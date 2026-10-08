import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import 'element-plus/dist/index.css'
import './styles.css'
import App from './App.vue'
import router from './router'
import UserPreferenceTable from './components/UserPreferenceTable.vue'

if ('scrollRestoration' in history) history.scrollRestoration = 'manual'

const app = createApp(App)
app.use(ElementPlus, { locale: zhCn }).use(router)
// 统一增强现有 el-table：只改变浏览器中的列展示，不接触接口数据和导出逻辑。
const registeredComponents = (app as unknown as { _context: { components: Record<string, unknown> } })._context.components
registeredComponents.ElTable = UserPreferenceTable
app.mount('#app')
