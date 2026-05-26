# 可观测性契约

> 统一规范见 `@../../references/oma/observability.md`。本文件为 hier 特定采集点。

| 采集点 | 触发条件 | 记录字段 |
|--------|---------|---------|
| hier_started | 拆解开始时 | `{input_path, expected_domains[]}` |
| hier_completed | 拆解完成时 | `{output_dir, sub_prd_count, quality_score}` |
| hier_entity_found | 核心实体识别 | `{entity_name, domain_assignment}` |
| hier_gate_passed | MECE 校验通过 | `{orthogonal_count, dependency_resolution}` |
