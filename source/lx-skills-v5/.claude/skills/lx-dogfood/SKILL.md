---
name: lx-dogfood
version: v1.0.0
description: 主动投喂狗粮 — 事故发生时趁热记录，处理完毕时提炼教训，让 Carror OS 和你意念通达
category: workflow
type: workflow
execution_mode: stepwise
enabled_by_default: true
when_to_use: "Use when user experiences an incident, discovers a pitfall, or wants to record a lesson learned. Trigger: '狗粮', '投喂', 'dogfood', '记录教训', '记住这个教训'."
harness_version: ">=6.3.0"
status: stable
role: "Dogfood recorder — capture incidents hot, extract lessons"
evidence_level: L3
triggers:
  - "狗粮"
  - "投喂"
  - "喂狗粮"
  - "投喂狗粮"
  - "意念通达"
  - "趁热记录"
  - "记录教训"
  - "踩坑记录"
  - "喂经验"
  - "记住这个教训"
  - "dogfood"
  - "dog food"
  - "feed dogfood"
  - "dogfooding"
  - "incident report"
  - "eat your own dog food"
body_ref: references/body.md
---
