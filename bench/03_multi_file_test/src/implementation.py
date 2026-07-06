#!/usr/bin/env python3
"""implementation.py — 用户模块实现层"""

from src.interface import UserSchema, validate_user


def format_user(user: UserSchema) -> str:
    """格式化用户信息为可读字符串"""
    return f"User({user.user_id}): {user.name}, age {user.age}, email {user.email}"


def create_user(data: dict) -> UserSchema:
    """创建用户并返回格式化信息"""
    user = validate_user(data)
    return user
