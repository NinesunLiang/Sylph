#!/usr/bin/env node
// TASK CONFIG — 任务配置加载器（机制通用化的唯一入口）
// 配置位置: <repo>/.omc/ui-autopilot/<task>/task.json
// 换项目/换原型 = 新建一个 task 目录 + task.json + gold-refresh，脚本零改动。
// 字段:
//   impl       string   实现页 URL（本地 dev server）
//   proto      string   原型页 URL（gold-refresh 用）
//   viewport   {w,h}    CSS 视口（gold 与 impl 必须一致，measure 硬守卫）
//   viewports  [{w,h,zones?}] 多断点（§十二，可选）；每断点独立 gold/measure，综合分取最短板
//   dsf        number   deviceScaleFactor（默认 2）
//   zones      [{name, box:[x,y,w,h]}]  CSS px 语义区域（measure 内部乘 dsf）
//   weights    {pixel,style,text}       综合分权重（默认 0.5/0.3/0.2）
//   typecheck  string   门禁 typecheck 命令（默认 'pnpm run typecheck'）
//   srcDirs    string[] 门禁回滚/污染检查目录（默认 ['src/', 'public/']）
//   wait       number   页面加载等待 ms（proto 慢流式可加大，默认 2500）
import { readFileSync, existsSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, resolve, join } from 'path';

// 脚本位于 <repo>/.claude/workflows/frontend-overnight/scripts/ui-restore/ → 仓库根 = 上 5 级
export const REPO_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '../../../../..');

export function loadTask(task) {
  const dir = join(REPO_ROOT, '.omc', 'ui-autopilot', task);
  const cfgPath = join(dir, 'task.json');
  if (!existsSync(cfgPath)) {
    console.error(`FATAL: 缺少任务配置 ${cfgPath}\n按 STYLE-DIFF-MECHANISM.md §十一 创建 task.json 后重试`);
    process.exit(2);
  }
  const raw = JSON.parse(readFileSync(cfgPath, 'utf8'));
  // 多断点（§十二）：viewports[] 每断点可带自有 zones（缺省回落顶层 zones）；
  // 未配 viewports = 单断点（legacy viewport + 顶层 zones），行为与通用化前完全一致
  const vpList = (Array.isArray(raw.viewports) && raw.viewports.length
    ? raw.viewports.map(v => ({ w: v.w ?? 1510, h: v.h ?? 860, zones: v.zones || raw.zones || [] }))
    : [{ w: raw.viewport?.w ?? 1510, h: raw.viewport?.h ?? 860, zones: raw.zones || [] }]
  ).map(v => ({ w: v.w, h: v.h, zones: v.zones.map(z => ({ name: z.name, box: z.box })) }));
  const cfg = {
    task,
    dir,
    goldDir: join(dir, 'gold'),
    outDir: join(dir, 'measurements', 'latest'),
    impl: raw.impl || 'http://localhost:9001/',
    proto: raw.proto || null,
    viewports: vpList,
    vw: vpList[0].w,
    vh: vpList[0].h,
    zones: vpList[0].zones,
    dsf: raw.dsf ?? 2,
    weights: { pixel: raw.weights?.pixel ?? 0.5, style: raw.weights?.style ?? 0.3, text: raw.weights?.text ?? 0.2 },
    typecheck: raw.typecheck || 'pnpm run typecheck',
    srcDirs: raw.srcDirs || ['src/', 'public/'],
    wait: raw.wait ?? 2500,
    states: raw.states || [],
  };
  if (!cfg.viewports[0].zones.length) {
    console.error(`FATAL: ${cfgPath} 缺少 zones（语义区域定义，CSS px）`);
    process.exit(2);
  }
  return cfg;
}
