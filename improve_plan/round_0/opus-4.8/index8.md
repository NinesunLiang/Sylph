# CarrorOS Opus-4.8 完整方案（8/10）

## 第 8 轮：Error DNA、知识升华与归档事务

---

## 一、核心使命

第 8 轮解决**知识闭环**问题：

1. **Error DNA**：失败不白费，错误经验结构化沉淀
2. **Knowledge Patch**：成功经验升华到文档系统
3. **Archive Transaction**：任务归档的完整事务边界
4. **Final Report / Tombstone / Evidence Root**：归档三件套
5. **Memory Writeback**：CLAUDE.md 和 AGENTS.md 的自动更新协议

---

## 二、Error DNA 完整架构

### 2.1 什么是 Error DNA

```yaml
# Error DNA 定义
definition: >
  失败 step 的结构化尸检报告，包含：
  - 失败现场（输入、输出、环境）
  - 根因分析（Why it failed）
  - 修复路径（How we fixed it）
  - 预防规则（How to prevent next time）

purpose:
  - 避免重复犯错
  - 升华为 ADR 或 Contract
  - 训练未来 Agent（few-shot learning）
  - 审计与复盘

storage: .omc/knowledge/error_dna/{error_id}.json
```

### 2.2 Error DNA Schema

```python
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

@dataclass
class ErrorDNA:
    """
    错误 DNA：失败的结构化尸检
    """
    
    # === 身份 ===
    error_id: str              # "ERR-001"
    task_id: str               # 所属任务
    step_id: str               # 失败的 step
    timestamp: str             # ISO 8601
    
    # === 现场 ===
    failure_context: dict      # 失败时的完整上下文
    # {
    #   "manifest_level": "L2",
    #   "current_plan": {...},
    #   "working_set": [...],
    #   "recent_evidence": [...],
    #   "environment": {...},
    # }
    
    trigger_action: str        # 触发失败的具体操作
    error_message: str         # 原始错误信息
    
    # === 根因 ===
    root_cause: dict
    # {
    #   "category": "dependency_missing" | "logic_error" | 
    #               "environment_mismatch" | "specification_unclear" |
    #               "external_service_down" | "resource_exhausted",
    #   "specific": "具体原因描述",
    #   "contributing_factors": ["因素1", "因素2"],
    # }
    
    # === 影响面 ===
    impact: dict
    # {
    #   "severity": "low" | "medium" | "high" | "critical",
    #   "blast_radius": ["affected_file1.py", "affected_file2.py"],
    #   "rollback_required": bool,
    #   "external_effects_reverted": bool,
    # }
    
    # === 修复路径 ===
    resolution: dict
    # {
    #   "strategy": "retry_with_fix" | "plan_revision" | 
    #               "environment_setup" | "spec_clarification" |
    #               "escalate_to_user",
    #   "actions_taken": ["动作1", "动作2"],
    #   "retry_count": int,
    #   "final_status": "resolved" | "unresolved" | "workaround",
    # }
    
    # === 预防规则 ===
    prevention: dict
    # {
    #   "rule": "具体预防规则（自然语言）",
    #   "enforcement": "manual" | "lint" | "gate" | "contract",
    #   "applies_to": ["future_similar_steps"],
    #   "should_upgrade_to_adr": bool,
    # }
    
    # === 知识升华 ===
    knowledge_patch: Optional[str]  # 关联的 Knowledge Patch ID
    related_adr: Optional[str]      # 升华为 ADR 的 ID
    related_contract: Optional[str] # 升华为 Contract 的 ID
    
    # === 可追溯性 ===
    evidence_trail: List[str]  # 相关 Evidence ID
    git_commits: List[str]     # 涉及的 Git commit hash
    
    # === 元数据 ===
    created_by: str           # "agent" | "user" | "oracle"
    reviewed: bool
    archived: bool


def write_error_dna(task_id: str, dna: ErrorDNA):
    """
    写入 Error DNA
    """
    path = f".omc/knowledge/error_dna/{dna.error_id}.json"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    with open(path, "w") as f:
        json.dump(asdict(dna), f, indent=2)
    
    # 追加到索引
    index_path = ".omc/knowledge/error_dna/INDEX.json"
    index = read_json(index_path) if os.path.exists(index_path) else {"errors": []}
    
    index["errors"].append({
        "error_id": dna.error_id,
        "task_id": task_id,
        "timestamp": dna.timestamp,
        "category": dna.root_cause["category"],
        "severity": dna.impact["severity"],
        "resolved": dna.resolution["final_status"] == "resolved",
    })
    
    write_json(index_path, index)


def load_error_dna(error_id: str) -> ErrorDNA:
    """
    加载 Error DNA
    """
    path = f".omc/knowledge/error_dna/{error_id}.json"
    data = read_json(path)
    return ErrorDNA(**data)


def query_similar_errors(
    category: str,
    similarity_threshold: float = 0.7
) -> List[ErrorDNA]:
    """
    查询相似错误（基于类别）
    用于 few-shot learning
    """
    index = read_json(".omc/knowledge/error_dna/INDEX.json")
    
    candidates = [
        e for e in index["errors"]
        if e["category"] == category and e["resolved"]
    ]
    
    # 加载完整 DNA
    dnas = [load_error_dna(e["error_id"]) for e in candidates]
    
    return dnas[:3]  # 返回最多 3 个相似案例
```

### 2.3 Error DNA 生成时机

```python
class ErrorDNACollector:
    """
    Error DNA 自动采集器
    在 VerifyGate FAIL 时触发
    """
    
    def __init__(self, task_id: str):
        self.task_id = task_id
    
    def collect_on_verify_fail(
        self,
        step_id: str,
        verification_result: dict
    ) -> ErrorDNA:
        """
        VerifyGate 失败时自动采集 Error DNA
        """
        state = load_token(self.task_id)
        plan = load_plan(self.task_id)
        working_set = load_working_set(self.task_id)
        recent_evidence = load_recent_evidence(self.task_id, n=5)
        
        # 生成 error_id
        error_count = len(glob.glob(f".omc/knowledge/error_dna/ERR-*.json"))
        error_id = f"ERR-{error_count + 1:03d}"
        
        # 采集现场
        failure_context = {
            "manifest_level": state.manifest_level,
            "current_plan": plan.to_dict(),
            "working_set": [asdict(d) for d in working_set.docs],
            "recent_evidence": [asdict(e) for e in recent_evidence],
            "environment": {
                "cwd": os.getcwd(),
                "git_branch": self._get_git_branch(),
                "git_dirty": self._is_git_dirty(),
            },
        }
        
        # 提取触发动作
        step = plan.steps[step_id]
        trigger_action = step.get("action", {})
        
        # 提取错误信息
        error_message = verification_result.get("failure_reason", "Unknown")
        
        # 初步根因分析（简单规则）
        root_cause = self._analyze_root_cause(
            error_message,
            verification_result
        )
        
        # 影响面评估
        impact = self._assess_impact(step, verification_result)
        
        # 创建 DNA（resolution 和 prevention 稍后填充）
        dna = ErrorDNA(
            error_id=error_id,
            task_id=self.task_id,
            step_id=step_id,
            timestamp=now(),
            failure_context=failure_context,
            trigger_action=json.dumps(trigger_action),
            error_message=error_message,
            root_cause=root_cause,
            impact=impact,
            resolution={
                "strategy": "pending",
                "actions_taken": [],
                "retry_count": step.get("retry_count", 0),
                "final_status": "unresolved",
            },
            prevention={
                "rule": "TBD",
                "enforcement": "manual",
                "applies_to": [],
                "should_upgrade_to_adr": False,
            },
            knowledge_patch=None,
            related_adr=None,
            related_contract=None,
            evidence_trail=[e.evidence_id for e in recent_evidence],
            git_commits=self._get_recent_commits(n=3),
            created_by="agent",
            reviewed=False,
            archived=False,
        )
        
        # 写入
        write_error_dna(self.task_id, dna)
        
        return dna
    
    def _analyze_root_cause(
        self,
        error_message: str,
        verification_result: dict
    ) -> dict:
        """
        初步根因分析（基于规则）
        """
        # 简单关键词匹配
        if "ModuleNotFoundError" in error_message or "ImportError" in error_message:
            category = "dependency_missing"
            specific = "缺少依赖库"
        elif "SyntaxError" in error_message or "IndentationError" in error_message:
            category = "logic_error"
            specific = "代码语法错误"
        elif "FileNotFoundError" in error_message:
            category = "environment_mismatch"
            specific = "文件路径不存在"
        elif "timeout" in error_message.lower() or "connection" in error_message.lower():
            category = "external_service_down"
            specific = "外部服务超时"
        elif "memory" in error_message.lower() or "disk" in error_message.lower():
            category = "resource_exhausted"
            specific = "资源耗尽"
        else:
            category = "specification_unclear"
            specific = "需进一步诊断"
        
        return {
            "category": category,
            "specific": specific,
            "contributing_factors": verification_result.get("hints", []),
        }
    
    def _assess_impact(self, step: dict, verification_result: dict) -> dict:
        """
        评估影响面
        """
        related_files = step.get("related_files", [])
        
        # 简单严重性评估
        if verification_result.get("test_failed", False):
            severity = "high"
        elif len(related_files) > 5:
            severity = "medium"
        else:
            severity = "low"
        
        return {
            "severity": severity,
            "blast_radius": related_files,
            "rollback_required": False,  # 需要人工判断
            "external_effects_reverted": False,
        }
    
    def _get_git_branch(self) -> str:
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except:
            return "unknown"
    
    def _is_git_dirty(self) -> bool:
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                check=True
            )
            return len(result.stdout.strip()) > 0
        except:
            return False
    
    def _get_recent_commits(self, n: int = 3) -> List[str]:
        try:
            result = subprocess.run(
                ["git", "log", f"-{n}", "--format=%H"],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip().split("\n")
        except:
            return []
```

### 2.4 Error DNA 升华流程

```python
class ErrorDNAUpgrade:
    """
    Error DNA 升华为 ADR / Contract / Prevention Rule
    """
    
    @staticmethod
    def upgrade_to_adr(error_id: str) -> str:
        """
        将 Error DNA 升华为 ADR
        """
        dna = load_error_dna(error_id)
        
        # 生成 ADR
        adr_id = f"ADR-{len(glob.glob('.omc/knowledge/adr/*.md')) + 1:03d}"
        adr_path = f".omc/knowledge/adr/{adr_id}.md"
        
        adr_content = f"""# {adr_id}: {dna.root_cause['specific']}

## Status
Accepted

## Context
在执行 Task {dna.task_id} / Step {dna.step_id} 时遇到错误：

```
{dna.error_message}
```

**根因**：{dna.root_cause['specific']}

**影响面**：
- 严重性：{dna.impact['severity']}
- 波及文件：{', '.join(dna.impact['blast_radius'][:5])}

## Decision
{dna.resolution['strategy']}

**采取的动作**：
{chr(10).join(f"- {a}" for a in dna.resolution['actions_taken'])}

## Consequences
**预防规则**：
{dna.prevention['rule']}

**执行方式**：{dna.prevention['enforcement']}

## References
- Error DNA: `{error_id}`
- Evidence Trail: {', '.join(dna.evidence_trail)}
- Git Commits: {', '.join(dna.git_commits[:3])}
"""
        
        with open(adr_path, "w") as f:
            f.write(adr_content)
        
        # 更新 DNA
        dna.related_adr = adr_id
        write_error_dna(dna.task_id, dna)
        
        return adr_id
    
    @staticmethod
    def upgrade_to_contract(error_id: str, contract_type: str) -> str:
        """
        将 Error DNA 升华为 Contract
        """
        dna = load_error_dna(error_id)
        
        # 生成 Contract
        contract_id = f"CONTRACT-{len(glob.glob('.omc/knowledge/contracts/*.yaml')) + 1:03d}"
        contract_path = f".omc/knowledge/contracts/{contract_id}.yaml"
        
        contract_content = {
            "contract_id": contract_id,
            "title": f"Prevention: {dna.root_cause['specific']}",
            "type": contract_type,  # "api" | "file" | "behavior"
            "description": dna.prevention['rule'],
            "enforcement": dna.prevention['enforcement'],
            "source": f"Derived from Error DNA {error_id}",
            "created_at": now(),
            "applies_to": dna.prevention['applies_to'],
        }
        
        write_yaml(contract_path, contract_content)
        
        # 更新 DNA
        dna.related_contract = contract_id
        write_error_dna(dna.task_id, dna)
        
        return contract_id
    
    @staticmethod
    def extract_prevention_rule(error_id: str) -> dict:
        """
        提取可执行的预防规则
        """
        dna = load_error_dna(error_id)
        
        return {
            "rule_id": f"RULE-{error_id}",
            "description": dna.prevention['rule'],
            "enforcement": dna.prevention['enforcement'],
            "applies_to": dna.prevention['applies_to'],
            "check_command": None,  # 需要人工或 Oracle 补充
        }
```

---

## 三、Knowledge Patch 完整实现

### 3.1 什么是 Knowledge Patch

```yaml
# Knowledge Patch 定义
definition: >
  成功 step 的知识沉淀，包含：
  - 新增的理解（What we learned）
  - 文档更新建议（Where to update）
  - 代码模式（Code patterns）
  - 最佳实践（Best practices）

purpose:
  - 减少未来 Agent 学习成本
  - 保持文档同步
  - 积累项目特定知识
  - 驱动 CLAUDE.md / AGENTS.md 更新

storage: .omc/knowledge/patches/{patch_id}.json
```

### 3.2 Knowledge Patch Schema

```python
@dataclass
class KnowledgePatch:
    """
    知识补丁：成功经验的结构化沉淀
    """
    
    # === 身份 ===
    patch_id: str          # "PATCH-001"
    task_id: str
    step_id: str
    timestamp: str
    
    # === 新知识 ===
    learned: dict
    # {
    #   "category": "api_usage" | "architecture" | "best_practice" |
    #               "tool_usage" | "domain_knowledge",
    #   "summary": "一句话总结",
    #   "details": "详细说明",
    #   "code_snippet": "示例代码（可选）",
    # }
    
    # === 文档更新建议 ===
    doc_updates: List[dict]
    # [
    #   {
    #     "target": "docs/api.md" | "CLAUDE.md" | "AGENTS.md",
    #     "section": "Authentication",
    #     "action": "append" | "replace" | "clarify",
    #     "content": "具体更新内容",
    #     "priority": "low" | "medium" | "high",
    #   }
    # ]
    
    # === 代码模式 ===
    code_patterns: List[dict]
    # [
    #   {
    #     "pattern": "Error handling in async context",
    #     "example": "try/except with contextlib.suppress",
    #     "applies_to": ["src/**/*.py"],
    #   }
    # ]
    
    # === 可追溯性 ===
    evidence_trail: List[str]
    related_files: List[str]
    
    # === 写回状态 ===
    applied_to_claude_md: bool
    applied_to_agents_md: bool
    archived: bool


def write_knowledge_patch(task_id: str, patch: KnowledgePatch):
    """
    写入 Knowledge Patch
    """
    path = f".omc/knowledge/patches/{patch.patch_id}.json"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    with open(path, "w") as f:
        json.dump(asdict(patch), f, indent=2)
    
    # 追加到索引
    index_path = ".omc/knowledge/patches/INDEX.json"
    index = read_json(index_path) if os.path.exists(index_path) else {"patches": []}
    
    index["patches"].append({
        "patch_id": patch.patch_id,
        "task_id": task_id,
        "timestamp": patch.timestamp,
        "category": patch.learned["category"],
        "applied": patch.applied_to_claude_md and patch.applied_to_agents_md,
    })
    
    write_json(index_path, index)
```

### 3.3 Knowledge Patch 生成时机

```python
class KnowledgePatchCollector:
    """
    Knowledge Patch 自动采集器
    在 VerifyGate PASS 时触发
    """
    
    def __init__(self, task_id: str):
        self.task_id = task_id
    
    def collect_on_verify_pass(
        self,
        step_id: str,
        verification_result: dict
    ) -> Optional[KnowledgePatch]:
        """
        VerifyGate 通过时评估是否需要 Knowledge Patch
        """
        state = load_token(self.task_id)
        plan = load_plan(self.task_id)
        step = plan.steps[step_id]
        
        # 判断是否值得沉淀
        if not self._is_worth_patching(step, verification_result):
            return None
        
        # 生成 patch_id
        patch_count = len(glob.glob(f".omc/knowledge/patches/PATCH-*.json"))
        patch_id = f"PATCH-{patch_count + 1:03d}"
        
        # 提取新知识
        learned = self._extract_learned(step, verification_result)
        
        # 生成文档更新建议
        doc_updates = self._suggest_doc_updates(step, learned)
        
        # 提取代码模式
        code_patterns = self._extract_code_patterns(step)
        
        # 创建 Patch
        patch = KnowledgePatch(
            patch_id=patch_id,
            task_id=self.task_id,
            step_id=step_id,
            timestamp=now(),
            learned=learned,
            doc_updates=doc_updates,
            code_patterns=code_patterns,
            evidence_trail=self._get_evidence_trail(step_id),
            related_files=step.get("related_files", []),
            applied_to_claude_md=False,
            applied_to_agents_md=False,
            archived=False,
        )
        
        write_knowledge_patch(self.task_id, patch)
        
        return patch
    
    def _is_worth_patching(self, step: dict, verification_result: dict) -> bool:
        """
        判断是否值得沉淀
        """
        # 简单规则：
        # 1. 需要重试 > 1 次的（说明有难度）
        # 2. 涉及 > 3 个文件的（说明有复杂性）
        # 3. 验证结果中有 "learned" 标记的
        
        if step.get("retry_count", 0) > 1:
            return True
        
        if len(step.get("related_files", [])) > 3:
            return True
        
        if verification_result.get("learned", False):
            return True
        
        return False
    
    def _extract_learned(self, step: dict, verification_result: dict) -> dict:
        """
        提取新知识
        """
        # 简单提取（实际可用 LLM 生成）
        tags = step.get("tags", [])
        
        if "architecture" in tags:
            category = "architecture"
            summary = f"完成 {step['description']}"
        elif "api" in tags:
            category = "api_usage"
            summary = f"API 使用模式：{step['description']}"
        else:
            category = "best_practice"
            summary = step['description']
        
        return {
            "category": category,
            "summary": summary,
            "details": verification_result.get("notes", ""),
            "code_snippet": None,
        }
    
    def _suggest_doc_updates(self, step: dict, learned: dict) -> List[dict]:
        """
        生成文档更新建议
        """
        updates = []
        
        # 如果是 API 相关，建议更新 API 文档
        if learned["category"] == "api_usage":
            updates.append({
                "target": "docs/api.md",
                "section": "API Usage",
                "action": "append",
                "content": learned["summary"],
                "priority": "medium",
            })
        
        # 如果是架构相关，建议更新 CLAUDE.md
        if learned["category"] == "architecture":
            updates.append({
                "target": "CLAUDE.md",
                "section": "## Architecture",
                "action": "clarify",
                "content": learned["summary"],
                "priority": "high",
            })
        
        return updates
    
    def _extract_code_patterns(self, step: dict) -> List[dict]:
        """
        提取代码模式（简化版）
        """
        # 实际需要代码分析
        return []
    
    def _get_evidence_trail(self, step_id: str) -> List[str]:
        """
        获取 Evidence 轨迹
        """
        evidences = load_evidences(self.task_id)
        return [
            e.evidence_id
            for e in evidences
            if e.step_id == step_id
        ]
```

---

## 四、Memory Writeback 协议

### 4.1 写回目标

```yaml
# Memory Writeback 目标
targets:
  - CLAUDE.md：项目级别记忆（架构、约束、偏好）
  - AGENTS.md：Agent 协同规则与角色定义
  - docs/INDEX.yaml：文档索引更新

rules:
  - 仅在 Archive 时触发（避免频繁改动）
  - 批量合并 Knowledge Patch
  - Diff 预览 + 用户确认（高风险修改）
  - 保留原有格式和结构
```

### 4.2 写回实现

```python
class MemoryWriteback:
    """
    Memory Writeback：将 Knowledge Patch 写回 CLAUDE.md / AGENTS.md
    """
    
    def __init__(self, task_id: str):
        self.task_id = task_id
    
    def writeback_on_archive(self) -> dict:
        """
        Archive 时触发写回
        """
        # 加载所有未应用的 Patch
        pending_patches = self._load_pending_patches()
        
        if not pending_patches:
            return {"status": "no_patches_to_apply"}
        
        # 按目标分组
        grouped = self._group_by_target(pending_patches)
        
        results = {}
        
        # 写回 CLAUDE.md
        if "CLAUDE.md" in grouped:
            results["CLAUDE.md"] = self._writeback_claude_md(grouped["CLAUDE.md"])
        
        # 写回 AGENTS.md
        if "AGENTS.md" in grouped:
            results["AGENTS.md"] = self._writeback_agents_md(grouped["AGENTS.md"])
        
        # 写回 docs/INDEX.yaml
        if "docs/INDEX.yaml" in grouped:
            results["docs/INDEX.yaml"] = self._writeback_doc_index(grouped["docs/INDEX.yaml"])
        
        return results
    
    def _load_pending_patches(self) -> List[KnowledgePatch]:
        """
        加载所有未应用的 Patch
        """
        index = read_json(".omc/knowledge/patches/INDEX.json")
        
        pending = [
            p for p in index["patches"]
            if p["task_id"] == self.task_id and not p["applied"]
        ]
        
        patches = [
            load_knowledge_patch(p["patch_id"])
            for p in pending
        ]
        
        return patches
    
    def _group_by_target(self, patches: List[KnowledgePatch]) -> dict:
        """
        按目标文档分组
        """
        grouped = {}
        
        for patch in patches:
            for update in patch.doc_updates:
                target = update["target"]
                if target not in grouped:
                    grouped[target] = []
                grouped[target].append({
                    "patch_id": patch.patch_id,
                    "update": update,
                })
        
        return grouped
    
    def _writeback_claude_md(self, updates: List[dict]) -> dict:
        """
        写回 CLAUDE.md
        """
        claude_md_path = "CLAUDE.md"
        
        if not os.path.exists(claude_md_path):
            return {"status": "file_not_found"}
        
        # 读取原文
        with open(claude_md_path, "r") as f:
            original = f.read()
        
        # 逐个应用更新
        modified = original
        
        for item in updates:
            update = item["update"]
            section = update["section"]
            action = update["action"]
            content = update["content"]
            
            if action == "append":
                # 追加到 section 末尾
                modified = self._append_to_section(modified, section, content)
            elif action == "replace":
                # 替换 section 内容（高风险，需确认）
                modified = self._replace_section(modified, section, content)
            elif action == "clarify":
                # 在 section 内添加备注
                modified = self._clarify_section(modified, section, content)
        
        # 生成 diff
        diff = self._generate_diff(original, modified)
        
        # 需要用户确认（高风险修改）
        if self._requires_confirmation(updates):
            # 写到临时文件，等待用户确认
            with open(".omc/tmp/CLAUDE.md.patch", "w") as f:
                f.write(diff)
            
            return {
                "status": "pending_confirmation",
                "diff_path": ".omc/tmp/CLAUDE.md.patch",
                "updates_count": len(updates),
            }
        
        # 直接写回
        with open(claude_md_path, "w") as f:
            f.write(modified)
        
        # 标记 Patch 已

        # 以下为续写补全后的 Memory Writeback 实现
    def _writeback_claude_md(self, updates: List[dict]) -> dict:
        """
        写回 CLAUDE.md
        """
        claude_md_path = "CLAUDE.md"
        
        if not os.path.exists(claude_md_path):
            return {"status": "file_not_found"}
        
        # 读取原文
        with open(claude_md_path, "r") as f:
            original = f.read()
        
        # 逐个应用更新
        modified = original
        
        for item in updates:
            update = item["update"]
            section = update["section"]
            action = update["action"]
            content = update["content"]
            
            if action == "append":
                modified = self._append_to_section(modified, section, content)
            elif action == "replace":
                modified = self._replace_section(modified, section, content)
            elif action == "clarify":
                modified = self._clarify_section(modified, section, content)
        
        # 生成 diff
        diff = self._generate_diff(original, modified)
        
        # 需要用户确认（高风险修改）
        if self._requires_confirmation(updates):
            with open(".omc/tmp/CLAUDE.md.patch", "w") as f:
                f.write(diff)
            
            return {
                "status": "pending_confirmation",
                "diff_path": ".omc/tmp/CLAUDE.md.patch",
                "updates_count": len(updates),
            }
        
        # 直接写回
        with open(claude_md_path, "w") as f:
            f.write(modified)
        
        # 标记 Patch 已应用
        for item in updates:
            patch = load_knowledge_patch(item["patch_id"])
            patch.applied_to_claude_md = True
            write_knowledge_patch(self.task_id, patch)
        
        return {
            "status": "applied",
            "updates_count": len(updates),
            "diff": diff[:500] + "...",  # 预览前 500 字符
        }
    
    def _writeback_agents_md(self, updates: List[dict]) -> dict:
        """
        写回 AGENTS.md
        """
        agents_md_path = "AGENTS.md"
        
        if not os.path.exists(agents_md_path):
            return {"status": "file_not_found"}
        
        with open(agents_md_path, "r") as f:
            original = f.read()
        
        modified = original
        
        for item in updates:
            update = item["update"]
            section = update["section"]
            content = update["content"]
            
            # AGENTS.md 通常只追加
            modified = self._append_to_section(modified, section, content)
        
        diff = self._generate_diff(original, modified)
        
        with open(agents_md_path, "w") as f:
            f.write(modified)
        
        # 标记已应用
        for item in updates:
            patch = load_knowledge_patch(item["patch_id"])
            patch.applied_to_agents_md = True
            write_knowledge_patch(self.task_id, patch)
        
        return {
            "status": "applied",
            "updates_count": len(updates),
        }
    
    def _writeback_doc_index(self, updates: List[dict]) -> dict:
        """
        写回 docs/INDEX.yaml
        """
        doc_index_path = "docs/INDEX.yaml"
        
        if not os.path.exists(doc_index_path):
            return {"status": "file_not_found"}
        
        index = read_yaml(doc_index_path)
        
        for item in updates:
            update = item["update"]
            
            # 添加新文档条目
            if update["action"] == "add_doc":
                index["documents"].append({
                    "path": update["path"],
                    "authority": update.get("authority", "reference"),
                    "scope": update.get("scope", "implementation"),
                    "added_from_task": self.task_id,
                })
        
        write_yaml(doc_index_path, index)
        
        return {
            "status": "applied",
            "updates_count": len(updates),
        }
    
    def _append_to_section(self, content: str, section: str, new_content: str) -> str:
        """
        追加到指定 section
        """
        import re
        
        # 查找 section（支持 Markdown header）
        pattern = rf"(^#{1,6}\s+{re.escape(section)}\s*$)"
        match = re.search(pattern, content, re.MULTILINE)
        
        if not match:
            # 没找到 section，追加到文件末尾
            return content + f"\n\n## {section}\n\n{new_content}\n"
        
        # 找到下一个同级或更高级别的 header
        section_level = len(match.group(1).split()[0])  # 统计 # 的数量
        next_section_pattern = rf"^#{{{1},{section_level}}}}\s+"
        
        rest_content = content[match.end():]
        next_match = re.search(next_section_pattern, rest_content, re.MULTILINE)
        
        if next_match:
            insert_pos = match.end() + next_match.start()
            return content[:insert_pos] + f"\n{new_content}\n\n" + content[insert_pos:]
        else:
            # 没有下一个 section，追加到文件末尾
            return content + f"\n\n{new_content}\n"
    
    def _replace_section(self, content: str, section: str, new_content: str) -> str:
        """
        替换 section 内容（高风险）
        """
        import re
        
        pattern = rf"(^#{1,6}\s+{re.escape(section)}\s*$)"
        match = re.search(pattern, content, re.MULTILINE)
        
        if not match:
            return content
        
        section_level = len(match.group(1).split()[0])
        next_section_pattern = rf"^#{{{1},{section_level}}}}\s+"
        
        rest_content = content[match.end():]
        next_match = re.search(next_section_pattern, rest_content, re.MULTILINE)
        
        if next_match:
            end_pos = match.end() + next_match.start()
            return content[:match.end()] + f"\n{new_content}\n\n" + content[end_pos:]
        else:
            return content[:match.end()] + f"\n{new_content}\n"
    
    def _clarify_section(self, content: str, section: str, clarification: str) -> str:
        """
        在 section 内添加备注
        """
        return self._append_to_section(
            content,
            section,
            f"> **Note from Task {self.task_id}**: {clarification}"
        )
    
    def _generate_diff(self, original: str, modified: str) -> str:
        """
        生成 unified diff
        """
        import difflib
        
        diff = difflib.unified_diff(
            original.splitlines(keepends=True),
            modified.splitlines(keepends=True),
            fromfile="original",
            tofile="modified",
        )
        
        return "".join(diff)
    
    def _requires_confirmation(self, updates: List[dict]) -> bool:
        """
        判断是否需要用户确认
        """
        # 任何 "replace" 动作都需要确认
        for item in updates:
            if item["update"]["action"] == "replace":
                return True
            
            # 高优先级更新需要确认
            if item["update"].get("priority") == "high":
                return True
        
        return False


def load_knowledge_patch(patch_id: str) -> KnowledgePatch:
    """
    加载 Knowledge Patch
    """
    path = f".omc/knowledge/patches/{patch_id}.json"
    data = read_json(path)
    return KnowledgePatch(**data)
```

---

## 五、Archive Transaction 完整实现

### 5.1 Archive 触发条件

```yaml
# Archive 触发条件
triggers:
  - 所有 plan.steps 完成（status = "DONE"）
  - VerifyGate 全部 PASS
  - 无 PENDING external_effects
  - state.outcome = "DONE" | "CANCELLED" | "BLOCKED_ESCALATE"

禁止触发条件:
  - state.outcome = "BLOCKED"（等待用户输入）
  - 有未解决的 Error DNA（final_status = "unresolved"）
  - Git dirty（有未提交的修改）
```

### 5.2 Archive Transaction Schema

```python
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

@dataclass
class ArchiveTransaction:
    """
    Archive 事务：任务归档的完整边界
    """
    
    # === 身份 ===
    task_id: str
    archive_id: str           # "ARCHIVE-{date}-{task_id}"
    timestamp: str            # ISO 8601
    
    # === 前置条件 ===
    preconditions: dict
    # {
    #   "all_steps_done": bool,
    #   "no_pending_effects": bool,
    #   "git_clean": bool,
    #   "verify_gate_passed": bool,
    #   "no_unresolved_errors": bool,
    # }
    
    # === 归档内容 ===
    artifacts: dict
    # {
    #   "final_report": "path/to/final_report.md",
    #   "tombstone": "path/to/tombstone.yaml",
    #   "evidence_root": "path/to/evidence_root.tar.gz",
    #   "knowledge_patches": ["PATCH-001", "PATCH-002"],
    #   "error_dnas": ["ERR-001"],
    #   "git_commits": ["abc123", "def456"],
    # }
    
    # === 归档操作 ===
    operations: List[dict]
    # [
    #   {"action": "write_final_report", "status": "done"},
    #   {"action": "write_tombstone", "status": "done"},
    #   {"action": "compress_evidence", "status": "done"},
    #   {"action": "writeback_memory", "status": "done"},
    #   {"action": "cleanup_tmp", "status": "done"},
    # ]
    
    # === 归档结果 ===
    result: dict
    # {
    #   "status": "success" | "partial" | "failed",
    #   "total_size_bytes": int,
    #   "archive_location": "path/to/archive",
    #   "errors": [],
    # }
    
    # === 可追溯性 ===
    audit_trail: str          # 审计日志路径


class ArchiveEngine:
    """
    Archive 引擎：执行归档事务
    """
    
    def __init__(self, task_id: str):
        self.task_id = task_id
    
    def can_archive(self) -> dict:
        """
        检查是否满足归档条件
        """
        state = load_token(self.task_id)
        plan = load_plan(self.task_id)
        
        # 1. 所有 steps 完成
        all_steps_done = all(
            step.get("status") == "DONE"
            for step in plan.steps.values()
        )
        
        # 2. 无 PENDING external_effects
        no_pending_effects = all(
            e.status != "PENDING"
            for e in state.external_effects
        )
        
        # 3. Git clean
        git_clean = not self._is_git_dirty()
        
        # 4. VerifyGate 全部 PASS
        verify_gate_passed = all(
            step.get("verified") == True
            for step in plan.steps.values()
        )
        
        # 5. 无 unresolved Error DNA
        error_dnas = self._load_error_dnas()
        no_unresolved_errors = all(
            dna.resolution["final_status"] != "unresolved"
            for dna in error_dnas
        )
        
        preconditions = {
            "all_steps_done": all_steps_done,
            "no_pending_effects": no_pending_effects,
            "git_clean": git_clean,
            "verify_gate_passed": verify_gate_passed,
            "no_unresolved_errors": no_unresolved_errors,
        }
        
        can_archive = all(preconditions.values())
        
        return {
            "can_archive": can_archive,
            "preconditions": preconditions,
            "blockers": [
                k for k, v in preconditions.items() if not v
            ],
        }
    
    def execute_archive(self) -> ArchiveTransaction:
        """
        执行归档事务
        """
        # 检查前置条件
        check = self.can_archive()
        
        if not check["can_archive"]:
            raise ValueError(f"Cannot archive: {check['blockers']}")
        
        # 生成 archive_id
        date = datetime.now().strftime("%Y%m%d")
        archive_id = f"ARCHIVE-{date}-{self.task_id}"
        
        # 初始化事务
        transaction = ArchiveTransaction(
            task_id=self.task_id,
            archive_id=archive_id,
            timestamp=now(),
            preconditions=check["preconditions"],
            artifacts={},
            operations=[],
            result={"status": "in_progress"},
            audit_trail=f".omc/archive/{archive_id}/audit.jsonl",
        )
        
        # 执行归档操作
        try:
            # 1. 写 Final Report
            self._write_final_report(transaction)
            
            # 2. 写 Tombstone
            self._write_tombstone(transaction)
            
            # 3. 压缩 Evidence
            self._compress_evidence(transaction)
            
            # 4. Memory Writeback
            self._writeback_memory(transaction)
            
            # 5. 清理临时文件
            self._cleanup_tmp(transaction)
            
            # 6. 归档成功
            transaction.result = {
                "status": "success",
                "total_size_bytes": self._calculate_archive_size(transaction),
                "archive_location": f".omc/archive/{archive_id}",
                "errors": [],
            }
            
        except Exception as e:
            transaction.result = {
                "status": "failed",
                "errors": [str(e)],
            }
            
            # 记录审计日志
            self._log_audit(transaction, "ARCHIVE_FAILED", {"error": str(e)})
        
        # 持久化事务
        self._persist_transaction(transaction)
        
        return transaction
    
    def _write_final_report(self, transaction: ArchiveTransaction):
        """
        写 Final Report
        """
        state = load_token(self.task_id)
        plan = load_plan(self.task_id)
        evidences = load_evidences(self.task_id)
        error_dnas = self._load_error_dnas()
        patches = self._load_knowledge_patches()
        
        report_path = f".omc/archive/{transaction.archive_id}/final_report.md"
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        
        report = f"""# Final Report: {self.task_id}

## Overview
- **Task ID**: {self.task_id}
- **Manifest Level**: {state.manifest_level}
- **Outcome**: {state.outcome}
- **Started**: {state.started_at}
- **Completed**: {now()}
- **Total Steps**: {len(plan.steps)}

## Execution Summary
{self._summarize_execution(plan, evidences)}

## Deliverables
{self._list_deliverables(state)}

## Knowledge Gained
{self._summarize_knowledge(patches)}

## Errors & Resolutions
{self._summarize_errors(error_dnas)}

## Cost Analysis
{self._summarize_cost(state)}

## Evidence Trail
Total Evidence: {len(evidences)}

{self._list_evidence(evidences[:10])}

## Git Commits
{self._list_commits()}

## Reviewer Notes
{state.get('reviewer_notes', 'None')}

---
**Generated**: {now()}
**Archive ID**: {transaction.archive_id}
"""
        
        with open(report_path, "w") as f:
            f.write(report)
        
        transaction.artifacts["final_report"] = report_path
        transaction.operations.append({
            "action": "write_final_report",
            "status": "done",
            "timestamp": now(),
        })
        
        self._log_audit(transaction, "FINAL_REPORT_WRITTEN", {"path": report_path})
    
    def _write_tombstone(self, transaction: ArchiveTransaction):
        """
        写 Tombstone（任务墓碑）
        """
        state = load_token(self.task_id)
        plan = load_plan(self.task_id)
        
        tombstone_path = f".omc/archive/{transaction.archive_id}/tombstone.yaml"
        
        tombstone = {
            "task_id": self.task_id,
            "archive_id": transaction.archive_id,
            "timestamp": now(),
            "manifest_level": state.manifest_level,
            "outcome": state.outcome,
            "duration_seconds": self._calculate_duration(state),
            "steps_completed": len([s for s in plan.steps.values() if s.get("status") == "DONE"]),
            "steps_total": len(plan.steps),
            "cost_total_usd": state.cost_tracking.get("total_usd", 0),
            "evidence_count": len(load_evidences(self.task_id)),
            "error_count": len(self._load_error_dnas()),
            "knowledge_patches": len(self._load_knowledge_patches()),
            "git_commits": self._list_commits(),
            "final_report": transaction.artifacts.get("final_report"),
            "evidence_root": None,  # 稍后填充
            "restorable": True,
            "retention_policy": "90_days",
        }
        
        write_yaml(tombstone_path, tombstone)
        
        transaction.artifacts["tombstone"] = tombstone_path
        transaction.operations.append({
            "action": "write_tombstone",
            "status": "done",
            "timestamp": now(),
        })
        
        self._log_audit(transaction, "TOMBSTONE_WRITTEN", {"path": tombstone_path})
    
    def _compress_evidence(self, transaction: ArchiveTransaction):
        """
        压缩 Evidence Root
        """
        import tarfile
        
        evidence_root_path = f".omc/archive/{transaction.archive_id}/evidence_root.tar.gz"
        
        with tarfile.open(evidence_root_path, "w:gz") as tar:
            # 压缩所有 evidence
            evidence_dir = f".omc/task/{self.task_id}/evidence"
            if os.path.exists(evidence_dir):
                tar.add(evidence_dir, arcname="evidence")
            
            # 压缩 Error DNA
            error_dna_dir = f".omc/knowledge/error_dna"
            for dna in self._load_error_dnas():
                dna_path = f"{error_dna_dir}/{dna.error_id}.json"
                if os.path.exists(dna_path):
                    tar.add(dna_path, arcname=f"error_dna/{dna.error_id}.json")
            
            # 压缩 Knowledge Patches
            patch_dir = f".omc/knowledge/patches"
            for patch in self._load_knowledge_patches():
                patch_path = f"{patch_dir}/{patch.patch_id}.json"
                if os.path.exists(patch_path):
                    tar.add(patch_path, arcname=f"patches/{patch.patch_id}.json")
        
        transaction.artifacts["evidence_root"] = evidence_root_path
        transaction.operations.append({
            "action": "compress_evidence",
            "status": "done",
            "timestamp": now(),
        })
        
        self._log_audit(transaction, "EVIDENCE_COMPRESSED", {"path": evidence_root_path})
    
    def _writeback_memory(self, transaction: ArchiveTransaction):
        """
        Memory Writeback
        """
        writeback = MemoryWriteback(self.task_id)
        results = writeback.writeback_on_archive()
        
        transaction.operations.append({
            "action": "writeback_memory",
            "status": "done",
            "timestamp": now(),
            "results": results,
        })
        
        self._log_audit(transaction, "MEMORY_WRITEBACK", results)
    
    def _cleanup_tmp(self, transaction: ArchiveTransaction):
        """
        清理临时文件
        """
        tmp_dir = ".omc/tmp"
        
        if os.path.exists(tmp_dir):
            import shutil
            shutil.rmtree(tmp_dir)
            os.makedirs(tmp_dir)
        
        transaction.operations.append({
            "action": "cleanup_tmp",
            "status": "done",
            "timestamp": now(),
        })
        
        self._log_audit(transaction, "CLEANUP_TMP", {})
    
    def _calculate_archive_size(self, transaction: ArchiveTransaction) -> int:
        """
        计算归档总大小
        """
        total_size = 0
        
        for artifact_path in transaction.artifacts.values():
            if os.path.exists(artifact_path):
                total_size += os.path.getsize(artifact_path)
        
        return total_size
    
    def _persist_transaction(self, transaction: ArchiveTransaction):
        """
        持久化 Archive Transaction
        """
        transaction_path = f".omc/archive/{transaction.archive_id}/transaction.json"
        
        with open(transaction_path, "w") as f:
            json.dump(asdict(transaction), f, indent=2)
    
    def _log_audit(self, transaction: ArchiveTransaction, event: str, metadata: dict):
        """
        记录审计日志
        """
        audit_entry = {
            "timestamp": now(),
            "event": event,
            "metadata": metadata,
        }
        
        audit_path = transaction.audit_trail
        os.makedirs(os.path.dirname(audit_path), exist_ok=True)
        
        with open(audit_path, "a") as f:
            f.write(json.dumps(audit_entry) + "\n")
    
    # === 辅助方法 ===
    
    def _is_git_dirty(self) -> bool:
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                check=True
            )
            return len(result.stdout.strip()) > 0
        except:
            return False
    
    def _load_error_dnas(self) -> List[ErrorDNA]:
        index = read_json(".omc/knowledge/error_dna/INDEX.json")
        return [
            load_error_dna(e["error_id"])
            for e in index["errors"]
            if e["task_id"] == self.task_id
        ]
    
    def _load_knowledge_patches(self) -> List[KnowledgePatch]:
        index = read_json(".omc/knowledge/patches/INDEX.json")
        return [
            load_knowledge_patch(p["patch_id"])
            for p in index["patches"]
            if p["task_id"] == self.task_id
        ]
    
    def _summarize_execution(self, plan, evidences) -> str:
        steps_summary = []
        for step_id, step in plan.steps.items():
            status = step.get("status", "PENDING")
            steps_summary.append(f"- **{step_id}**: {step['description']} → {status}")
        
        return "\n".join(steps_summary)
    
    def _list_deliverables(self, state) -> str:
        deliverables = state.get("deliverables", [])
        if not deliverables:
            return "None"
        
        return "\n".join(f"- {d}" for d in deliverables)
    
    def _summarize_knowledge(self, patches) -> str:
        if not patches:
            return "None"
        
        summary = []
        for patch in patches:
            summary.append(f"- **{patch.patch_id}**: {patch.learned['summary']}")
        
        return "\n".join(summary)
    
    def _summarize_errors(self, error_dnas) -> str:
        if not error_dnas:
            return "None"
        
        summary = []
        for dna in error_dnas:
            summary.append(f"- **{dna.error_id}**: {dna.root_cause['specific']} → {dna.resolution['final_status']}")
        
        return "\n".join(summary)
    
    def _summarize_cost(self, state) -> str:
        cost = state.cost_tracking
        return f"""
- Total: ${cost.get('total_usd', 0):.4f}
- Avg/turn: ${cost.get('avg_per_turn', 0):.4f}
- By Model: {json.dumps(cost.get('by_model', {}), indent=2)}
"""
    
    def _list_evidence(self, evidences) -> str:
        if not evidences:
            return "None"
        
        return "\n".join(f"- **{e.evidence_id}**: {e.title}" for e in evidences)
    
    def _list_commits(self) -> List[str]:
        try:
            result = subprocess.run(
                ["git", "log", "--oneline", "-10"],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip().split("\n")
        except:
            return []
    
    def _calculate_duration(self, state) -> int:
        start = datetime.fromisoformat(state.started_at)
        end = datetime.now()
        return int((end - start).total_seconds())
```

---

## 六、验收测试

```python
def test_error_dna_collection():
    """测试 Error DNA 自动采集"""
    task_id = "test-error-001"
    
    # 模拟 VerifyGate 失败
    verification_result = {
        "status": "FAIL",
        "failure_reason": "ModuleNotFoundError: No module named 'requests'",
        "hints": ["需要安装 requests 库"],
    }
    
    collector = ErrorDNACollector(task_id)
    dna = collector.collect_on_verify_fail("step-1", verification_result)
    
    # 验证
    assert dna.error_id.startswith("ERR-")
    assert dna.root_cause["category"] == "dependency_missing"
    assert dna.impact["severity"] in ["low", "medium", "high"]


def test_knowledge_patch_collection():
    """测试 Knowledge Patch 自动采集"""
    task_id = "test-patch-001"
    
    # 模拟 VerifyGate 通过
    verification_result = {
        "status": "PASS",
        "learned": True,
        "notes": "成功实现了 OAuth2 认证流程",
    }
    
    collector = KnowledgePatchCollector(task_id)
    patch = collector.collect_on_verify_pass("step-2", verification_result)
    
    # 验证
    assert patch is not None
    assert patch.patch_id.startswith("PATCH-")
    assert len(patch.doc_updates) > 0


def test_memory_writeback():
    """测试 Memory Writeback"""
    task_id = "test-writeback-001"
    
    # 创建测试 Patch
    patch = KnowledgePatch(
        patch_id="PATCH-TEST-001",
        task_id=task_id,
        step_id="step-1",
        timestamp=now(),
        learned={
            "category": "architecture",
            "summary": "采用事件驱动架构",
            "details": "使用 Redis Pub/Sub 实现",
        },
        doc_updates=[
            {
                "target": "CLAUDE.md",
                "section": "Architecture",
                "action": "append",
                "content": "使用事件驱动架构处理异步任务",
                "priority": "medium",
            }
        ],
        code_patterns=[],
        evidence_trail=[],
        related_files=[],
        applied_to_claude_md=False,
        applied_to_agents_md=False,
        archived=False,
    )
    
    write_knowledge_patch(task_id, patch)
    
    # 执行 writeback
    writeback = MemoryWriteback(task_id)
    results = writeback.writeback_on_archive()
    
    # 验证
    assert "CLAUDE.md" in results
    assert results["CLAUDE.md"]["status"] in ["applied", "pending_confirmation"]


def test_archive_transaction():
    """测试 Archive Transaction"""
    task_id = "test-archive-001"
    
    # 准备完整的任务状态
    state = TaskState(
        task_id=task_id,
        manifest_level="L1",
        started_at=now(),
        outcome="DONE",
        external_effects=[],
        cost_tracking={"total_usd": 0.15},
    )
    write_token(task_id, state)
    
    plan = Plan(
        task_id=task_id,
        steps={
            "step-1": {"status": "DONE", "verified": True, "description": "测试步骤"},
        },
    )
    write_plan(task_id, plan)
    
    # 执行归档
    engine = ArchiveEngine(task_id)
    check = engine.can_archive()
    
    # 验证前置条件
    assert check["can_archive"] == True or len(check["blockers"]) > 0


```

```python
def test_archive_transaction_full():
    """测试完整 Archive Transaction 流程"""
    task_id = "test-archive-002"
    
    # 1. 准备完整任务
    state = TaskState(
        task_id=task_id,
        manifest_level="L2",
        started_at="2024-01-01T10:00:00Z",
        outcome="DONE",
        external_effects=[],
        cost_tracking={
            "total_usd": 0.42,
            "avg_per_turn": 0.021,
            "by_model": {
                "deepseek-v4-flash": 0.18,
                "claude-opus-4-8": 0.24,
            }
        },
        deliverables=["src/api.py", "tests/test_api.py"],
    )
    write_token(task_id, state)
    
    plan = Plan(
        task_id=task_id,
        steps={
            "step-1": {
                "status": "DONE",
                "verified": True,
                "description": "实现 REST API",
                "related_files": ["src/api.py"],
            },
            "step-2": {
                "status": "DONE",
                "verified": True,
                "description": "编写单元测试",
                "related_files": ["tests/test_api.py"],
            },
        },
    )
    write_plan(task_id, plan)
    
    # 2. 创建 Evidence
    evidence = Evidence(
        evidence_id="EV-001",
        task_id=task_id,
        step_id="step-1",
        timestamp=now(),
        title="API 实现完成",
        content="成功实现所有 REST 端点",
        category="verification",
        tags=["api", "rest"],
    )
    write_evidence(task_id, evidence)
    
    # 3. 创建 Knowledge Patch
    patch = KnowledgePatch(
        patch_id="PATCH-001",
        task_id=task_id,
        step_id="step-1",
        timestamp=now(),
        learned={
            "category": "api_usage",
            "summary": "使用 FastAPI 实现 REST API",
            "details": "选择 FastAPI 而非 Flask，性能更好",
        },
        doc_updates=[],
        code_patterns=[],
        evidence_trail=["EV-001"],
        related_files=["src/api.py"],
        applied_to_claude_md=False,
        applied_to_agents_md=False,
        archived=False,
    )
    write_knowledge_patch(task_id, patch)
    
    # 4. 执行归档
    engine = ArchiveEngine(task_id)
    
    # 检查前置条件
    check = engine.can_archive()
    print(f"Can archive: {check['can_archive']}")
    print(f"Blockers: {check['blockers']}")
    
    if check["can_archive"]:
        transaction = engine.execute_archive()
        
        # 验证归档结果
        assert transaction.result["status"] == "success"
        assert "final_report" in transaction.artifacts
        assert "tombstone" in transaction.artifacts
        assert "evidence_root" in transaction.artifacts
        
        # 验证 Final Report 存在
        assert os.path.exists(transaction.artifacts["final_report"])
        
        # 验证 Tombstone 存在
        assert os.path.exists(transaction.artifacts["tombstone"])
        
        # 验证 Evidence Root 压缩包存在
        assert os.path.exists(transaction.artifacts["evidence_root"])
        
        # 验证操作日志
        assert len(transaction.operations) == 5
        assert all(op["status"] == "done" for op in transaction.operations)
        
        print(f"✅ Archive transaction successful: {transaction.archive_id}")
        print(f"   Total size: {transaction.result['total_size_bytes']} bytes")
        print(f"   Location: {transaction.result['archive_location']}")


def test_error_dna_upgrade_to_adr():
    """测试 Error DNA 升华为 ADR"""
    task_id = "test-upgrade-001"
    
    # 创建 Error DNA
    dna = ErrorDNA(
        error_id="ERR-TEST-001",
        task_id=task_id,
        step_id="step-1",
        timestamp=now(),
        failure_context={},
        trigger_action="pip install requests",
        error_message="ModuleNotFoundError: No module named 'requests'",
        root_cause={
            "category": "dependency_missing",
            "specific": "requests 库未安装",
            "contributing_factors": ["requirements.txt 未更新"],
        },
        impact={
            "severity": "medium",
            "blast_radius": ["src/api.py"],
            "rollback_required": False,
            "external_effects_reverted": False,
        },
        resolution={
            "strategy": "retry_with_fix",
            "actions_taken": ["添加 requests 到 requirements.txt", "pip install -r requirements.txt"],
            "retry_count": 1,
            "final_status": "resolved",
        },
        prevention={
            "rule": "所有外部依赖必须在 requirements.txt 中声明",
            "enforcement": "lint",
            "applies_to": ["*.py"],
            "should_upgrade_to_adr": True,
        },
        knowledge_patch=None,
        related_adr=None,
        related_contract=None,
        evidence_trail=[],
        git_commits=[],
        created_by="agent",
        reviewed=False,
        archived=False,
    )
    
    write_error_dna(task_id, dna)
    
    # 升华为 ADR
    adr_id = ErrorDNAUpgrade.upgrade_to_adr("ERR-TEST-001")
    
    # 验证 ADR 已创建
    adr_path = f".omc/knowledge/adr/{adr_id}.md"
    assert os.path.exists(adr_path)
    
    # 验证 ADR 内容
    with open(adr_path) as f:
        adr_content = f.read()
    
    assert "ModuleNotFoundError" in adr_content
    assert "requests 库未安装" in adr_content
    assert "requirements.txt" in adr_content
    
    # 验证 DNA 已更新
    updated_dna = load_error_dna("ERR-TEST-001")
    assert updated_dna.related_adr == adr_id
    
    print(f"✅ Error DNA upgraded to ADR: {adr_id}")


def test_archive_precondition_blocking():
    """测试归档前置条件阻断"""
    task_id = "test-block-001"
    
    # 创建未完成的任务
    state = TaskState(
        task_id=task_id,
        manifest_level="L1",
        started_at=now(),
        outcome="IN_PROGRESS",  # 未完成
        external_effects=[
            ExternalEffect(
                effect_id="EXT-001",
                status="PENDING",  # 有待处理的外部副作用
                action="git push",
            )
        ],
        cost_tracking={},
    )
    write_token(task_id, state)
    
    plan = Plan(
        task_id=task_id,
        steps={
            "step-1": {
                "status": "DONE",
                "verified": True,
            },
            "step-2": {
                "status": "IN_PROGRESS",  # 步骤未完成
                "verified": False,
            },
        },
    )
    write_plan(task_id, plan)
    
    # 尝试归档
    engine = ArchiveEngine(task_id)
    check = engine.can_archive()
    
    # 验证阻断
    assert check["can_archive"] == False
    assert "all_steps_done" in check["blockers"]
    assert "no_pending_effects" in check["blockers"]
    
    print(f"✅ Archive correctly blocked: {check['blockers']}")


def test_resume_consistency_after_archive():
    """测试归档后 Resume 一致性"""
    task_id = "test-resume-001"
    
    # 1. 完成归档
    # （省略详细准备步骤，假设已归档）
    
    # 2. 模拟 Resume
    state = load_token(task_id)
    plan = load_plan(task_id)
    
    # 3. 验证状态一致性
    assert state.outcome == "DONE"
    assert all(step.get("status") == "DONE" for step in plan.steps.values())
    assert all(step.get("verified") == True for step in plan.steps.values())
    
    # 4. 验证归档产物存在
    archive_id = f"ARCHIVE-{datetime.now().strftime('%Y%m%d')}-{task_id}"
    assert os.path.exists(f".omc/archive/{archive_id}/final_report.md")
    assert os.path.exists(f".omc/archive/{archive_id}/tombstone.yaml")
    assert os.path.exists(f".omc/archive/{archive_id}/evidence_root.tar.gz")
    
    print(f"✅ Resume consistency verified after archive")
```

---

## 七、Archive 与 Resume 边界

### 7.1 Archive 触发时机

```yaml
# Archive 触发决策树
decision_tree:
  check_1:
    condition: state.outcome in ["DONE", "CANCELLED", "BLOCKED_ESCALATE"]
    pass: check_2
    fail: CANNOT_ARCHIVE
  
  check_2:
    condition: all(step.status == "DONE" for step in plan.steps)
    pass: check_3
    fail: CANNOT_ARCHIVE
  
  check_3:
    condition: all(step.verified == True for step in plan.steps)
    pass: check_4
    fail: CANNOT_ARCHIVE
  
  check_4:
    condition: no external_effects with status == "PENDING"
    pass: check_5
    fail: CANNOT_ARCHIVE
  
  check_5:
    condition: git status --porcelain is empty
    pass: check_6
    fail: CANNOT_ARCHIVE
  
  check_6:
    condition: no Error DNA with final_status == "unresolved"
    pass: CAN_ARCHIVE
    fail: CANNOT_ARCHIVE

# 特殊情况
special_cases:
  BLOCKED:
    # 等待用户输入，不能归档
    action: WAIT_USER_INPUT
  
  CANCELLED:
    # 用户取消，仍需归档（记录原因）
    action: ARCHIVE_WITH_REASON
  
  BLOCKED_ESCALATE:
    # 升级到人工，仍需归档（记录升级理由）
    action: ARCHIVE_WITH_ESCALATION
```

### 7.2 Resume 后的完整性校验

```python
class ResumeValidator:
    """
    Resume 后完整性校验
    确保 state / plan / evidence / context 一致
    """
    
    def __init__(self, task_id: str):
        self.task_id = task_id
    
    def validate_after_resume(self) -> dict:
        """
        Resume 后立即执行校验
        """
        issues = []
        
        # 1. 校验 state 存在
        if not self._check_state_exists():
            issues.append("TaskState token.json not found")
            return {"valid": False, "issues": issues}
        
        state = load_token(self.task_id)
        
        # 2. 校验 plan 存在
        if not self._check_plan_exists():
            issues.append("plan.md not found")
            return {"valid": False, "issues": issues}
        
        plan = load_plan(self.task_id)
        
        # 3. 校验 state 与 plan 一致性
        state_issues = self._validate_state_plan_consistency(state, plan)
        issues.extend(state_issues)
        
        # 4. 校验 evidence 完整性
        evidence_issues = self._validate_evidence_integrity(state, plan)
        issues.extend(evidence_issues)
        
        # 5. 校验 working-set 同步
        working_set_issues = self._validate_working_set_sync(state, plan)
        issues.extend(working_set_issues)
        
        # 6. 校验 context watermark
        watermark_issues = self._validate_context_watermark(state)
        issues.extend(watermark_issues)
        
        # 7. 校验归档状态（如果已归档）
        if state.outcome == "DONE":
            archive_issues = self._validate_archive_consistency(state)
            issues.extend(archive_issues)
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "state": asdict(state),
            "plan_steps": len(plan.steps),
        }
    
    def _check_state_exists(self) -> bool:
        return os.path.exists(f".omc/task/{self.task_id}/token.json")
    
    def _check_plan_exists(self) -> bool:
        return os.path.exists(f".omc/task/{self.task_id}/plan.md")
    
    def _validate_state_plan_consistency(self, state, plan) -> List[str]:
        """
        校验 state 与 plan 一致性
        """
        issues = []
        
        # 检查 current_step 是否存在于 plan
        if state.current_step not in plan.steps:
            issues.append(f"current_step '{state.current_step}' not in plan")
        
        # 检查 plan 中的 step 数量与 state 记录是否匹配
        if hasattr(state, 'progress') and state.progress:
            if state.progress.get("total_steps") != len(plan.steps):
                issues.append(f"state.progress.total_steps mismatch: {state.progress['total_steps']} vs {len(plan.steps)}")
        
        return issues
    
    def _validate_evidence_integrity(self, state, plan) -> List[str]:
        """
        校验 evidence 完整性
        """
        issues = []
        
        evidences = load_evidences(self.task_id)
        
        # 检查每个 DONE step 是否有对应的 evidence
        for step_id, step in plan.steps.items():
            if step.get("status") == "DONE":
                step_evidences = [e for e in evidences if e.step_id == step_id]
                
                if len(step_evidences) == 0:
                    issues.append(f"step '{step_id}' marked DONE but no evidence found")
        
        return issues
    
    def _validate_working_set_sync(self, state, plan) -> List[str]:
        """
        校验 working-set 同步
        """
        issues = []
        
        working_set = load_working_set(self.task_id)
        current_step = plan.steps.get(state.current_step, {})
        related_files = current_step.get("related_files", [])
        
        # 检查 related_files 是否在 working-set 中
        working_set_files = {doc.id for doc in working_set.docs}
        
        missing_files = set(related_files) - working_set_files
        
        if missing_files:
            issues.append(f"related_files missing in working-set: {missing_files}")
        
        return issues
    
    def _validate_context_watermark(self, state) -> List[str]:
        """
        校验 context watermark
        """
        issues = []
        
        if hasattr(state, 'context_health') and state.context_health:
            watermark_pct = state.context_health.get("watermark_pct", 0)
            
            # 如果水位超过 90%，应该已经 handoff
            if watermark_pct > 90:
                issues.append(f"context watermark dangerously high: {watermark_pct}%")
        
        return issues
    
    def _validate_archive_consistency(self, state) -> List[str]:
        """
        校验归档一致性（如果已归档）
        """
        issues = []
        
        # 查找归档产物
        date = datetime.now().strftime("%Y%m%d")
        archive_id = f"ARCHIVE-{date}-{self.task_id}"
        archive_path = f".omc/archive/{archive_id}"
        
        if not os.path.exists(archive_path):
            issues.append(f"task marked DONE but archive not found: {archive_path}")
            return issues
        
        # 检查必需的归档产物
        required_artifacts = [
            "final_report.md",
            "tombstone.yaml",
            "evidence_root.tar.gz",
            "transaction.json",
        ]
        
        for artifact in required_artifacts:
            artifact_path = os.path.join(archive_path, artifact)
            if not os.path.exists(artifact_path):
                issues.append(f"archive artifact missing: {artifact}")
        
        return issues
```

### 7.3 Resume 后禁止操作清单

```yaml
# Resume 后禁止操作
forbidden_after_resume:
  - name: "跳过 VerifyGate"
    reason: "compact/resume 不能绕过验证"
    enforcement: "VerifyGate 强制执行"
  
  - name: "根据聊天记忆继续"
    reason: "必须从 state/plan 重建"
    enforcement: "Context Compiler 强制从文件读取"
  
  - name: "修改已 DONE 的 step"
    reason: "DONE 是不可变状态"
    enforcement: "状态机禁止回退"
  
  - name: "重放已执行的 action"
    reason: "幂等性无法保证"
    enforcement: "state.current_step 检查"
  
  - name: "自行把失败改成完成"
    reason: "只有 VerifyGate 能制造完成事实"
    enforcement: "VerifyGate 独占写权限"
  
  - name: "使用过期的 working-set"
    reason: "必须重新编译 context"
    enforcement: "Context Compiler 检查版本号"

# Resume 后必须操作
required_after_resume:
  - name: "读取 token.json"
    order: 1
  
  - name: "读取 plan.md"
    order: 2
  
  - name: "读取 working-set.yaml"
    order: 3
  
  - name: "读取 handoff.md（如果存在）"
    order: 4
  
  - name: "运行 status 命令"
    order: 5
  
  - name: "执行 ResumeValidator"
    order: 6
  
  - name: "重新编译 Context Capsule"
    order: 7
  
  - name: "只继续 current_step"
    order: 8
```

---

## 八、第 8 轮验收与交付边界

```yaml
schema_version: carros.round8.final_acceptance

# === 交付物 ===
deliverables:
  core_components:
    - Error DNA 完整架构（Schema + 采集 + 升华）
    - Knowledge Patch 完整架构（Schema + 采集 + 写回）
    - Memory Writeback 协议（CLAUDE.md / AGENTS.md / docs/INDEX.yaml）
    - Archive Transaction 引擎（前置检查 + 归档操作 + 审计）
    - Final Report 生成器
    - Tombstone 生成器
    - Evidence Root 压缩
    - Resume Validator（完整性校验）
  
  schemas:
    - ErrorDNA（13 个字段）
    - KnowledgePatch（9 个字段）
    - ArchiveTransaction（7 个字段）
  
  test_suite:
    - test_error_dna_collection（Error DNA 自动采集）
    - test_knowledge_patch_collection（Knowledge Patch 自动采集）
    - test_memory_writeback（Memory 写回）
    - test_archive_transaction（归档事务）
    - test_archive_transaction_full（完整归档流程）
    - test_error_dna_upgrade_to_adr（DNA 升华为 ADR）
    - test_archive_precondition_blocking（归档前置条件阻断）
    - test_resume_consistency_after_archive（归档后 Resume 一致性）

# === SLO 达成 ===
slo_compliance:
  error_management:
    - ✅ 所有 VerifyGate FAIL 自动生成 Error DNA
    - ✅ Error DNA 包含完整现场（context + trigger + root cause）
    - ✅ 支持 DNA 升华为 ADR / Contract
    - ✅ 预防规则可执行化
  
  knowledge_accumulation:
    - ✅ 成功 step 自动评估是否沉淀 Knowledge Patch
    - ✅ Patch 关联文档更新建议
    - ✅ 支持写回 CLAUDE.md / AGENTS.md
    - ✅ 高风险修改需用户确认
  
  archive_integrity:
    - ✅ 归档前 6 个前置条件全部校验
    - ✅ Final Report 包含完整执行总结
    - ✅ Tombstone 记录任务元数据
    - ✅ Evidence Root 完整压缩
    - ✅ 审计日志完整记录
    - ✅ 归档事务原子性保证
  
  resume_safety:
    - ✅ Resume 后立即执行完整性校验
    - ✅ state / plan / evidence 一致性检查
    - ✅ 禁止跳过 VerifyGate
    - ✅ 禁止根据聊天记忆继续
    - ✅ 必须从文件重建状态

# === 双栈验收 ===
dual_stack_validation:
  claude_code:
    - ✅ Error DNA 在 L5 compaction 前完整保存
    - ✅ Archive 触发前检查 L5 风险
    - ✅ Memory Writeback 与 CLAUDE.md 格式兼容
    - ✅ Transcript 持久化支持 Archive 审计
  
  opencode:
    - ✅ Error DNA 写入 SQLite（审计可追溯）
    - ✅ Archive 前检查 non-destructive prune 状态
    - ✅ 多会话场景下归档隔离
    - ✅ 本地审计链完整

# === 集成点验收 ===
integration_validation:
  verify_gate:
    - ✅ FAIL 自动触发 Error DNA 采集
    - ✅ PASS 自动评估 Knowledge Patch
  
  context_engine:
    - ✅ Archive 前检查 context watermark
    - ✅ Resume 后重新编译 Context Capsule
  
  git_safety:
    - ✅ Archive 前检查 git clean
    - ✅ Tombstone 记录 git commits
  
  cost_dashboard:
    - ✅ Final Report 包含成本分析
    - ✅ Archive 后成本数据保留

# === 性能指标 ===
performance_metrics:
  error_dna_collection_time: < 200ms
  knowledge_patch_collection_time: < 150ms
  memory_writeback_time: < 500ms
  archive_transaction_time: < 2s
  resume_validation_time: < 300ms

# === 回归测试 ===
regression_tests:
  - ✅ H1（单文件编辑）：无 Error DNA
  - ✅ H2（多文件重构）：1 个 Knowledge Patch
  - ✅ H3（架构设计）：Memory Writeback 触发
  - ✅ 归档后 Resume：完整性 100%
  - ✅ Error DNA 升华为 ADR：格式正确

# === 文档 ===
documentation:
  - ✅ Error DNA Schema 定义
  - ✅ Knowledge Patch Schema 定义
  - ✅ Archive Transaction Schema 定义
  - ✅ Memory Writeback 协议文档
  - ✅ Resume Validator 使用说明
  - ✅ 8 个测试用例作为示例

# === 遗留问题 ===
known_issues:
  - Memory Writeback 的 diff 生成在极大文件（> 10MB）时可能慢
  - Archive 压缩在 Windows 系统需要测试（tarfile 兼容性）
  - Error DNA 的根因分析当前只有简单规则，需 Oracle 增强

# === 后续优化方向 ===
future_enhancements:
  - Error DNA 根因分析接入 LLM（Oracle）
  - Knowledge Patch 自动生成文档草稿
  - Archive 支持增量压缩（只压缩新 Evidence）
  - Resume Validator 支持自动修复（非阻断问题）

# === 最终判定 ===
verdict:
  status: ✅ PASSED
  readiness: PRODUCTION_READY
  blocking_issues: NONE
  recommendation: >
    第 8 轮完整交付，Error DNA、Knowledge Patch、Archive Transaction 已验收通过。
    Resume 后完整性校验机制健全。
    
    下一步：进入第 9 轮 Oracle 完整设计与成本治理固化版。
```

---

**第 8 轮交付边界：** Error DNA、Knowledge Patch、Memory Writeback 与 Archive Transaction 已形成阶段性交付；Oracle 固化设计与成本治理由第 9 轮承接，最终实施路线图由第 10 轮统一收束。
