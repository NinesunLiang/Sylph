"""

Tests for user module — needs update when schema changes.

"""

from fixture.interface import UserSchema, validate_user
from fixture.implementation import create_user, format_user


def test_validate_user():
    data = {"user_id": 1, "name": "Alice", "age": 30}
    user = validate_user(data)
    assert user.name == "Alice"
    assert user.age == 30
    # TODO: add email assertion when email field is added


def test_format_user():
    user = UserSchema(user_id=1, name="Alice", age=30)
    result = format_user(user)
    assert "Alice" in result
    assert "30" in result


def test_create_user():
    data = {"user_id": 1, "name": "Alice", "age": 30}
    user = create_user(data)
    assert user.name == "Alice"
