// 模型数据真值（gold/states/model-dropdown.delta.json + models-assets.json 生成，勿手改）
export interface ModelRow { name: string; logo: string; logoBg: string; logoInner: number; flame: boolean; caps: string[]; tag: string }


export const MODELS_BASIC: ModelRow[] = [
  { name: 'GPT-5.6 Luna', logo: '/assets/models/gpt.svg', logoBg: 'rgb(0, 0, 0)', logoInner: 14, flame: true, caps: ["eye", "toy-brick", "atom", "globe"], tag: '1M' },
  { name: 'GPT-5.4 mini', logo: '/assets/models/gpt.svg', logoBg: 'rgb(0, 0, 0)', logoInner: 14, flame: false, caps: ["eye", "toy-brick", "atom", "globe"], tag: '400K' },
  { name: 'GPT-5 mini', logo: '/assets/models/gpt.svg', logoBg: 'rgb(0, 0, 0)', logoInner: 14, flame: false, caps: ["eye", "toy-brick", "atom", "globe"], tag: '400K' },
  { name: 'Gemini 3 Flash', logo: '/assets/models/gemini.svg', logoBg: 'rgba(0, 0, 0, 0)', logoInner: 20, flame: true, caps: ["eye", "toy-brick", "globe"], tag: '1M' },
  { name: 'Deepseek V3', logo: '/assets/models/deepseek.svg', logoBg: 'rgb(77, 107, 254)', logoInner: 14, flame: false, caps: ["toy-brick", "globe"], tag: '64K' },
]
export const MODELS_ENHANCED: ModelRow[] = [
  { name: 'GPT-5.6 Terra', logo: '/assets/models/gpt.svg', logoBg: 'rgb(0, 0, 0)', logoInner: 14, flame: true, caps: ["eye", "toy-brick", "atom", "globe"], tag: '1M' },
  { name: 'GPT-5.6 Sol', logo: '/assets/models/gpt.svg', logoBg: 'rgb(0, 0, 0)', logoInner: 14, flame: true, caps: ["eye", "toy-brick", "atom", "globe"], tag: '1M' },
  { name: 'GPT-5.5', logo: '/assets/models/gpt.svg', logoBg: 'rgb(0, 0, 0)', logoInner: 14, flame: false, caps: ["eye", "toy-brick", "atom", "globe"], tag: '1M' },
  { name: 'Gemini 3.6 Flash', logo: '/assets/models/gemini.svg', logoBg: 'rgba(0, 0, 0, 0)', logoInner: 20, flame: true, caps: ["eye", "toy-brick", "atom", "globe"], tag: '1M' },
  { name: 'Gemini 3.1 Pro', logo: '/assets/models/gemini.svg', logoBg: 'rgba(0, 0, 0, 0)', logoInner: 20, flame: false, caps: ["eye", "toy-brick", "atom", "globe"], tag: '1M' },
  { name: 'Claude 5 Sonnet', logo: '/assets/models/claude.svg', logoBg: 'rgb(217, 119, 87)', logoInner: 14, flame: true, caps: ["eye", "toy-brick", "atom", "globe"], tag: '1M' },
  { name: 'Claude 5 Opus（10次/3h）', logo: '/assets/models/claude.svg', logoBg: 'rgb(217, 119, 87)', logoInner: 14, flame: true, caps: ["eye", "toy-brick", "atom", "globe"], tag: '1M' },
  { name: 'Grok-4.5', logo: '/assets/models/grok.svg', logoBg: 'rgb(0, 0, 0)', logoInner: 14, flame: true, caps: ["eye", "toy-brick", "atom", "globe"], tag: '256K' },
  { name: 'GPT-Image-2 画图', logo: '/assets/models/gpt.svg', logoBg: 'rgb(0, 0, 0)', logoInner: 14, flame: true, caps: ["eye"], tag: '1M' },
  { name: 'Grok Imagine 画图', logo: '/assets/models/grok.svg', logoBg: 'rgb(0, 0, 0)', logoInner: 14, flame: true, caps: ["eye"], tag: '1M' },
  { name: 'Nano Banana 2 画图', logo: '/assets/models/gemini.svg', logoBg: 'rgba(0, 0, 0, 0)', logoInner: 20, flame: true, caps: ["eye"], tag: '1M' },
  { name: 'Nano Banana Pro 画图（10次/3h）', logo: '/assets/models/gemini.svg', logoBg: 'rgba(0, 0, 0, 0)', logoInner: 20, flame: false, caps: ["eye"], tag: '1M' },
  { name: 'Claude 4.7 Opus（10次/3h）', logo: '/assets/models/claude.svg', logoBg: 'rgb(217, 119, 87)', logoInner: 14, flame: false, caps: ["eye", "toy-brick", "atom", "globe"], tag: '1M' },
  { name: 'Claude 4.8 Opus（10次/3h）', logo: '/assets/models/claude.svg', logoBg: 'rgb(217, 119, 87)', logoInner: 14, flame: true, caps: ["eye", "toy-brick", "atom", "globe"], tag: '1M' },
  { name: 'Claude 4.6 Sonnet', logo: '/assets/models/claude.svg', logoBg: 'rgb(217, 119, 87)', logoInner: 14, flame: false, caps: ["eye", "toy-brick", "atom", "globe"], tag: '1M' },
  { name: 'GPT-5.3 Codex', logo: '/assets/models/gpt.svg', logoBg: 'rgb(0, 0, 0)', logoInner: 14, flame: false, caps: ["eye", "toy-brick", "atom", "globe"], tag: '400K' },
  { name: 'GPT-5.4', logo: '/assets/models/gpt.svg', logoBg: 'rgb(0, 0, 0)', logoInner: 14, flame: false, caps: ["eye", "toy-brick", "atom", "globe"], tag: '1M' },
  { name: 'Gemini 3.5 Flash', logo: '/assets/models/gemini.svg', logoBg: 'rgba(0, 0, 0, 0)', logoInner: 20, flame: true, caps: ["eye", "toy-brick", "atom", "globe"], tag: '1M' },
  { name: 'Grok-4.1', logo: '/assets/models/grok.svg', logoBg: 'rgb(0, 0, 0)', logoInner: 14, flame: false, caps: ["eye", "toy-brick", "atom", "globe"], tag: '256K' },
  { name: 'Grok-3', logo: '/assets/models/grok.svg', logoBg: 'rgb(0, 0, 0)', logoInner: 14, flame: false, caps: ["globe"], tag: '200K' },
]

// 能力图标样式真值（逐行验证跨行一致）: icon → [颜色, 底色]
export const CAP_STYLE: Record<string, [string, string]> = {
  'eye': ['rgb(85, 180, 103)', 'rgb(244, 253, 235)'],
  'toy-brick': ['rgb(0, 114, 245)', 'rgb(252, 251, 255)'],
  'atom': ['rgb(189, 84, 198)', 'rgb(255, 246, 251)'],
  'globe': ['rgb(47, 162, 138)', 'rgb(239, 255, 248)'],
}
