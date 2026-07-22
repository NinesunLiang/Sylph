#!/usr/bin/env python3

import argparse, sys, json, subprocess


def run_diff(files: list):
    """提取实际变更"""
    cmd = "git diff HEAD -- " + " ".join(f'"{f}"' for f in files)
    # nosec B602: skill 层 CLI 工具，输入为内部 git 命令拼接，非用户原始输入
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)  # nosec B602
    return r.stdout

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--files", nargs='+', required=True, help="需要审查的文件列表")
    p.add_argument("--rules", default="references/knowledge/review-rules.md", help="引用的审查规范")
    args = p.parse_args()

    diff_text = run_diff(args.files)
    if not diff_text.strip():
        print(json.dumps({"status": "passed", "message": "No diff found."}, ensure_ascii=False))
        sys.exit(0)

    system_prompt = f"""你是一个极度严苛、不通人情的顶级 Security & QA 专家（盲审官）。不要理会任何代码原作者留下的解释性注释！你的唯一目标是：通过传入的实际 Diff 和以下审查规范，找出所有的安全漏洞、性能瓶颈、逻辑缺陷和格式违规。审查规范路径：{args.rules}请以极其挑剔的眼光审查。如果有违规，请列出 violations 并返回 REJECTED；如果完美无瑕，返回 PASSED。代码变更 (Diff):```diff\n{diff_text}\n``` """

    instruction = {
        "status": "requires_subagent_blind_review",
        "action": "请立即使用 `Task` 工具启动盲审",
        "subagent_type": "general",
        "prompt": system_prompt,
        "description": "Sub-agent A/B 对抗性盲审"
    }
    print(json.dumps(instruction, ensure_ascii=False, indent=2))
    sys.exit(0)

if __name__ == "__main__":
    main()
