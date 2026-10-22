#!/usr/bin/env python3
"""
QQ Bot pending confirmation notifier.
Reads ~/.hermes/memories/pending_user_confirm.json and pushes to QQ Bot home channel.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add Hermes to path
sys.path.insert(0, str(Path.home() / ".hermes" / "hermes-agent"))

from tools.send_message_tool import send_message_tool

PENDING_FILE = Path.home() / ".hermes" / "memories" / "pending_user_confirm.json"


async def send_qq_notification():
    """Send pending confirmations to QQ Bot."""
    if not PENDING_FILE.exists():
        print("No pending file")
        return

    with open(PENDING_FILE, "r", encoding="utf-8") as f:
        pending = json.load(f)

    if not pending:
        print("No pending confirmations")
        return

    # Send each pending item - use explicit target with chat_id
    for item in pending:
        if item.get("status") != "pending":
            continue

        obs = item["observation"]
        msg = (
            f"⚠️ **中置信确认**\n"
            f"ID: `{item['id']}`\n"
            f"标签: {obs.get('tag', 'unknown')}\n"
            f"内容: {obs.get('text', '')[:200]}\n"
            f"置信度: {obs.get('confidence', 0):.2f}\n"
            f"理由: {item.get('reason', '')[:100]}\n\n"
            f"回复 **通过** 或 **丢弃** + ID 即可定夺。"
        )

        # Use explicit target with chat_id instead of home channel
        result = send_message_tool({
            "action": "send",
            "target": "qqbot:34E032F377C79B9B4CF00E9A7072A8EC",
            "message": msg
        })
        print(f"Sent: {result}")


if __name__ == "__main__":
    asyncio.run(send_qq_notification())