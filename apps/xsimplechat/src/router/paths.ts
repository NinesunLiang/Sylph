// 路由路径唯一出口（宪法：禁止手写拼接）
// 所有路由跳转/链接必须经本文件生成。

export const paths = {
  home: "/",
  chat: (session?: string) => (session ? `/chat?session=${session}` : "/chat"),
  discover: "/discover",
  assistant: (slug: string) => `/discover/assistant/${encodeURIComponent(slug)}`,
  translation: "/translation",
  files: "/files",
  settings: "/settings",
  member: "/member",
} as const;
