## 完整流程图

```
mermaidflow
chart TD A[Phase 0: Intake] --> B[Phase 1: Research] B --> GR{Gate-R} GR -->|"未通过"| B GR -->|"通过"| C[Phase 1.5: Uncertainty Scan] C --> GU{Gate-U} GU -->|"未通过"| C GU -->|"通过"| D[Phase 2: Plan 结构规划] D --> GP{Gate-P} GP -->|"未通过"| D GP -->|"通过"| E[Phase 2-E: 写作] E --> F[Phase 3: Self-Eval 8维自评] F --> SC{分数判断} SC -->|"<45"| E2[回 Phase 2 重写最低分2维] E2 --> F SC -->|"45-59: 修复P0+P1"| FIX1[修复 P0+P1] FIX1 --> H SC -->|"60-74: 修复P0"| FIX2[修复 P0] FIX2 --> H SC -->|"≥75"| H[Phase 4: Expert Review Loop] H --> EL{专家循环} EL -->|"有P0，Round≤3"| FIX[修复缺陷] FIX --> H EL -->|"无P0 / Round>3"| I[Phase 5: Polish 轻量清理] I --> GE{Gate-E} GE -->|"未通过"| I GE -->|"通过"| J[✅ PRD 交付 + 附录F待人工填写]
 style J fill:#e8f5e9,stroke:#4CAF50 style H fill:#fff3e0,stroke:#FF9800 style FIX1 fill:#fce4ec,stroke:#e91e63 style FIX2 fill:#fff8e1,stroke:#ff9800
```

---
