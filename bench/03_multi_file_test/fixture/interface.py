#!/usr/bin/env python3
"""interface.py — 用户模块接口定义"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class UserSchema:
    user_id: int
    name: str
    age: int
    # TODO: add email field
    email: str = ""


def validate_user(data: dict) -> UserSchema:
    """从字典创建 UserSchema"""
    return UserSchema(
        user_id=data["user_id"],
        name=data["name"],
        age=data["age"],
    )
