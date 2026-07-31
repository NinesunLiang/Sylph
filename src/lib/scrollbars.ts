// 全局滚动条显隐（gold 真值: macOS overlay 风格——静止隐藏、滚动显示、细条、导轨透明）
// 原理: 捕获阶段监听 document scroll → 给滚动元素挂 .is-scrolling，停止 800ms 后摘除
// 样式基类在 src/styles/global.scss（::-webkit-scrollbar-thumb 默认透明，.is-scrolling 时上色）
// 任意元素无需接入——overflow:auto 的容器自动获得该行为

const timers = new WeakMap<Element, ReturnType<typeof setTimeout>>()

export function initScrollbars() {
  document.addEventListener('scroll', (e) => {
    const el = e.target
    if (!(el instanceof HTMLElement)) return
    el.classList.add('is-scrolling')
    const prev = timers.get(el)
    if (prev) clearTimeout(prev)
    timers.set(el, setTimeout(() => el.classList.remove('is-scrolling'), 800))
  }, { capture: true, passive: true })
}
