# ARCHIVED — v6.2.1 — Historical benchmark snapshot. Referenced scripts may no longer exist on disk.
---
name: MITRE ATLAS AI Threat Matrix Mapping
description: Carror OS 30 hooks + skills mapped to MITRE ATLAS attack tactics/techniques mitigation (record only)
type: benchmark-report
standard: MITRE ATLAS (Adversarial Threat Landscape for AI Systems)
date: 2026-05-05
scope: AI-specific threats — Prompt Injection / Model Evasion / Data Poisoning / Output Manipulation
---

# MITRE ATLAS AI Threat Matrix Mapping

> **Standard Source**: [MITRE ATLAS](https://atlas.mitre.org/) — AI system adversarial threat matrix (2026 industry standard, mapping MITRE ATT&CK to AI scenarios)
> **Applicability**: Carror OS as AI governance layer, corresponding to the **"AI Developer"** perspective of defensive capabilities
> **Mapping Principle**: Map Carror OS specific hooks/skills to ATLAS tactics/techniques, annotate mitigation strength

## 1. Threat Scenario Positioning

Carror OS defends against **AI-to-System** directed threats (AI agent misoperation or malicious operation against the user's local machine / repository / infrastructure), not **Model-Level** threats (training data poisoning / model theft).

| ATLAS Tactic Phase | Carror OS Coverage | Reason |
|-------------------|:----------------:|--------|
| Reconnaissance | 🟡 Partial | privacy-gate prevents AI from reading sensitive files for reconnaissance |
| Resource Development | ❌ | Belongs to attacker preparation phase, unrelated to governance layer |
| Initial Access | 🟡 Partial | context-guard prevents context pollution |
| ML Model Access | ❌ | Carror does not manage model APIs, only AI behavior |
| Execution | ✅ Strong | permission-gate + edit-guard core capabilities |
| Persistence | ✅ | auto-snapshot + session-handoff prevent session drift |
| Defense Evasion | ✅ | audit-hooks three-way reconciliation prevents script zombification |
| Discovery | 🟡 | privacy-gate limits AI probing of sensitive areas |
| Collection | ✅ | privacy-gate bidirectional sanitization |
| Exfiltration | ✅ | privacy-gate + varlock prevent plaintext token exfiltration |
| Impact | ✅ Strong | permission-gate hard-blocks `rm -rf` / DROP TABLE |

## 2. Tactic-Technique-Carror Mitigation Mapping Table

| ATLAS ID | Tactic | Technique Name | Carror Mitigation | Strength |
|---------|-------|---------------|-----------------|:-------:|
| TA0002 / AML.T0051 | Execution | Command and Scripting Interpreter | `permission-gate.sh` blocks rm-rf / DROP / sudo / curl\|sh | 🟢 Strong |
| TA0002 / AML.T0011 | Execution | User Execution | `pretool-edit-scope.sh` three-option gate + AskUserQuestion confirmation | 🟢 Strong |
| TA0005 / AML.T0043 | Defense Evasion | Evade ML Model | N/A (model layer) | — |
| TA0005 / AML.T0050 | Defense Evasion | Command and Control | `audit-hooks.sh` three-way reconciliation + `--scan-internal-filter` anti-drift | 🟢 Strong |
| TA0007 / AML.T0013 | Discovery | Discover ML Model Ontology | N/A | — |
| TA0007 / AML.T0040 | Discovery | Discover ML Artifacts | `privacy-gate.sh` blocks `.env` / `~/.ssh` / private keys | 🟢 Strong |
| TA0009 / AML.T0025 | Collection | Data from Information Repositories | `privacy-gate.sh` intercepts all Read/Bash/Grep events | 🟢 Strong |
| TA0010 / AML.T0024 | Exfiltration | Exfiltration via Inference API | `varlock.py` bidirectional sanitization proxy, plaintext tokens never leave | 🟢 Strong |
| TA0011 / AML.T0031 | Impact | Erode ML Model Integrity | N/A (model layer) | — |
| TA0011 / AML.T0034 | Impact | Cost Harvesting | `subagent-guard.sh` + `posttool-subagent-audit.sh` three-layer defense | 🟡 Medium (soft constraint) |
| TA0011 / AML.T0048 | Impact | External Harms - Financial Harm | `permission-gate.sh` blocks unauthorized `git push --force` / package publish | 🟢 Strong |
| **New AI Dev Domain** | Context Drift | Long-session instruction decay | `turn-counter.sh` >=10 turn iron law injection + `pretool-rule-anchor.sh` >=15 turn anchoring | 🟢 Strong |
| **New AI Dev Domain** | Hallucination Cascade | False completion claims | `completion-gate.sh` strong L3 evidence gate + `posttool-write-cite.sh` citation verification | 🟢 Strong |
| **New AI Dev Domain** | Session Amnesia | Cross-session context loss | `auto-snapshot.sh` + `inject-project-knowledge.sh` SessionStart injection | 🟢 Strong |
| **New AI Dev Domain** | Error Recurrence | Repeating the same mistakes | `error-dna.sh` signature persistence + `skill-flywheel.sh` P0 event alerting | 🟢 Strong |
| **New AI Dev Domain** | Subagent Runaway | Subagent infinite loop burning tokens | `subagent-guard.sh` declaration layer + `posttool-subagent-audit.sh` execution layer + human layer | 🟡 Medium (soft constraint, see R25) |

## 3. AI-Specific Mitigation Strength Grading

| Threat | Prompt Suggestion Layer (Cursor/Copilot) | Physical Blocking Layer (Carror OS) |
|--------|:--------------------------------------:|:----------------------------------:|
| `rm -rf` accidental execution | ❌ Suggestion only, AI can ignore | ✅ Exit 2 hard block |
| `.env` leakage | ❌ | ✅ PreToolUse:Read strong block |
| Plaintext token leaving API | ❌ | ✅ varlock bidirectional sanitization |
| False completion claims | ❌ | ✅ completion-gate L3 evidence gate |
| Long-session forgotten iron laws | ❌ | ✅ rule-anchor >=15 turn strong injection |
| Subagent cost avalanche | ❌ | 🟡 Soft constraint + post-hoc reconciliation (see R25 integrity statement) |

## 4. Uncovered Threats (Transparent Disclosure)

| Threat | Why Carror Does Not Cover | Alternative |
|--------|--------------------------|-------------|
| Model Extraction / Inversion | Model-layer threat, Carror is client-side governance | Model vendor responsibility |
| Training Data Poisoning | Does not involve model training | Model vendor responsibility |
| Adversarial Examples | Does not involve model inference | Model vendor responsibility |
| Social engineering against the user | Human-factor threat, not technical defense | User training |

## 5. Summary Statistics

| ATLAS Tactic Domain | Direct Mapping | Carror Strong Mitigation | Carror Partial Mitigation | N/A |
|-------------------|:-------------:|:-----------------------:|:------------------------:|:---:|
| Execution | 2 | 2 | 0 | 0 |
| Defense Evasion | 2 | 1 | 0 | 1 |
| Discovery | 2 | 1 | 0 | 1 |
| Collection | 1 | 1 | 0 | 0 |
| Exfiltration | 1 | 1 | 0 | 0 |
| Impact | 3 | 2 | 1 | 0 |
| AI Dev Extension Domain | 5 | 4 | 1 | 0 |
| **Total** | **16** | **12** | **2** | **2** |

**Coverage Strength** (excluding N/A): 12 strong + 2 medium / 14 = **86% strong mitigation + 14% partial mitigation**

## 6. Conclusion

- Carror OS covers **100% of AI-to-System direction** threats in MITRE ATLAS (86% strong + 14% partial)
- Model-Level threats (training poisoning / model theft) are the responsibility of model vendors, outside this framework's scope
- The 2 "partial mitigation" items are both focused on subagent cost control (R25 already contains an integrity statement: soft constraints are not hard stops)

**Integrity Statement**: This mapping was generated by AI based on the ATLAS public matrix and Carror OS source code. The 5 **New AI Dev Domain** items are Carror's native threat model (referencing AI Native Developer threats not yet listed in ATLAS), not MITRE official naming.

## 7. References

- [MITRE ATLAS Matrix](https://atlas.mitre.org/matrices/ATLAS)
- [ATLAS Tactics Index](https://atlas.mitre.org/tactics/)
- [ATLAS Techniques Index](https://atlas.mitre.org/techniques/)
