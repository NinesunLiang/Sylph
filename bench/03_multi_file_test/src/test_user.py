"""

Tests for user module.

"""

from src.interface import UserSchema, validate_user
from src.implementation import create_user, format_user


def test_validate_user():
    data = {"user_id": 1, "name": "Alice", "age": 30, "email": "alice@example.com"}
    user = validate_user(data)
    assert user.name == "Alice"
    assert user.age == 30
    assert user.email == "alice@example.com"


def test_format_user():
    user = UserSchema(user_id=1, name="Alice", age=30, email="alice@example.com")
    result = format_user(user)
    assert "Alice" in result
    assert "30" in result
    assert "alice@example.com" in result


def test_create_user():
    data = {"user_id": 1, "name": "Alice", "age": 30, "email": "alice@example.com"}
    user = create_user(data)
    assert user.name == "Alice"
    assert user.email == "alice@example.com"
