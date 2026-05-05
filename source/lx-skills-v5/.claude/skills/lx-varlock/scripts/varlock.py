#!/usr/bin/env python3

"""

varlock.py — 隐私脱敏代理管理器 (Data Leakage Prevention)

用于处理含有敏感密钥/密码的文件和命令，通过双向映射替换，保证明文绝不泄露到 AI 的上下文。
执行端负责将脱敏的占位符恢复为真实数据落盘/运行。

用法:
 python3 varlock.py set <key> <value>              # 设置本地脱敏变量 (请在普通终端运行)
 python3 varlock.py list                            # 展示已脱敏的键值
 python3 varlock.py rm <key>                        # 删除键值
 python3 varlock.py run "<命令含 {KEY}>"             # 脱敏代理执行
 python3 varlock.py read <file_path>                # 读取文件并向 AI 输出脱敏后内容
 python3 varlock.py write <file_path> "<内容>"       # AI 写入脱敏内容，执行端恢复明文落盘
"""
import argparse, sys, json, os, subprocess
from pathlib import Path

VAULT_FILE = Path(".omc/state/varlock.json")


def load_vault() -> dict:
    if VAULT_FILE.exists():
        try:
            return json.loads(VAULT_FILE.read_text())
        except Exception:
            return {}
    return {}


def save_vault(data: dict):
    VAULT_FILE.parent.mkdir(parents=True, exist_ok=True)
    VAULT_FILE.write_text(json.dumps(data, indent=2))
    os.chmod(VAULT_FILE, 0o600)


# 正向脱敏：将真实数据替换为 [MASKED_KEY] (读给 AI 看)
def mask_content(content: str, vault: dict) -> str:
    for k, v in vault.items():
        if v:  # 不替换空串
            content = content.replace(v, f"[MASKED_{k}]")
    return content


# 反向恢复：将 [MASKED_KEY] 或 {KEY} 替换为真实数据 (执行端落盘或运行)
def restore_content(content: str, vault: dict) -> str:
    for k, v in vault.items():
        # 兼容 [MASKED_KEY] 和 {KEY} 两种占位符格式
        content = content.replace(f"[MASKED_{k}]", v)
        content = content.replace(f"{{{k}}}", v)
    return content


def main():
    p = argparse.ArgumentParser(description="隐私脱敏代理管理器 (Varlock)")
    p.add_argument("action", choices=["set", "list", "rm", "run", "read", "write"])
    p.add_argument("args", nargs=argparse.REMAINDER)
    args = p.parse_args()

    vault = load_vault()

    if args.action == "set":
        if len(args.args) < 2:
            print(json.dumps({"error": "Usage: varlock.py set <key> <value>"}))
            sys.exit(1)
        key = args.args[0]
        value = " ".join(args.args[1:])
        vault[key] = value
        save_vault(vault)
        print(json.dumps({
            "status": "locked",
            "key": key,
            "message": f"Secret securely saved and available as [MASKED_{key}] or {{{key}}}"
        }, ensure_ascii=False))

    elif args.action == "list":
        masked = {k: f"[MASKED_{k}]" for k in vault.keys()}
        print(json.dumps({"status": "ok", "vault": masked}, ensure_ascii=False, indent=2))

    elif args.action == "rm":
        if not args.args:
            print(json.dumps({"error": "Usage: varlock.py rm <key>"}))
            sys.exit(1)
        key = args.args[0]
        if key in vault:
            del vault[key]
            save_vault(vault)
            print(json.dumps({"status": "removed", "key": key}))
        else:
            print(json.dumps({"status": "not_found"}))

    elif args.action == "read":
        if not args.args:
            print(json.dumps({"error": "Usage: varlock.py read <file_path>"}), file=sys.stderr)
            sys.exit(1)
        filepath = Path(args.args[0])
        if not filepath.exists():
            print(json.dumps({"error": f"File not found: {filepath}"}), file=sys.stderr)
            sys.exit(1)
        raw_content = filepath.read_text(encoding="utf-8")
        # 脱敏后吐给 AI
        safe_content = mask_content(raw_content, vault)
        print(safe_content)
        sys.exit(0)

    elif args.action == "write":
        if len(args.args) < 2:
            print(json.dumps({"error": "Usage: varlock.py write <file_path> \"<content>\""}), file=sys.stderr)
            sys.exit(1)
        filepath = Path(args.args[0])
        safe_content = args.args[1]
        # 恢复真实数据并落盘
        real_content = restore_content(safe_content, vault)
        try:
            filepath.write_text(real_content, encoding="utf-8")
            print(json.dumps({
                "status": "success",
                "message": f"File {filepath} securely written with restored secrets."
            }, ensure_ascii=False))
            sys.exit(0)
        except Exception as e:
            print(json.dumps({"error": f"Failed to write file: {e}"}), file=sys.stderr)
            sys.exit(2)

    elif args.action == "run":
        if not args.args:
            print(json.dumps({"error": "Usage: varlock.py run '<command>'"}), file=sys.stderr)
            sys.exit(1)

        raw_cmd = " ".join(args.args)
        # 反向恢复命令中的真实密码进行执行
        real_cmd = restore_content(raw_cmd, vault)

        try:
            r = subprocess.run(real_cmd, shell=True, capture_output=True, text=True)
            code = r.returncode
            out_text = r.stdout
            err_text = r.stderr
        except Exception as e:
            code = 1
            out_text = ""
            err_text = str(e)

        # 代理执行完成后，将输出结果再次脱敏返回给 AI
        safe_out = mask_content(out_text, vault)
        safe_err = mask_content(err_text, vault)

        print(json.dumps({
            "exit_code": code,
            "stdout": safe_out.strip(),
            "stderr": safe_err.strip(),
        }, ensure_ascii=False, indent=2))
        sys.exit(2 if code != 0 else 0)


if __name__ == "__main__":
    main()
