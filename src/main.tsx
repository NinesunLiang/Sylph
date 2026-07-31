import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.tsx'
import { initScrollbars } from './lib/scrollbars'

initScrollbars() // 全局滚动条基类行为：滚动显示 / 静止隐藏

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
