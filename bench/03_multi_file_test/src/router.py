#!/usr/bin/env python3
"""router.py — 用户模块路由注册"""

from src.interface import UserSchema
from src.implementation import create_user, format_user


def handle_create_user(data: dict) -> str:
    """处理创建用户请求"""
    user = create_user(data)
    return format_user(user)
