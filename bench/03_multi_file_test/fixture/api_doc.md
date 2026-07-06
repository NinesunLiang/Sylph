# User Module API Documentation

## UserSchema

| Field | Type | Description |
|-------|------|-------------|
| user_id | int | User identifier |
| name | str | User display name |
| age | int | User age |
| email | str | User email (optional) |

## Endpoints

### create_user(data) → UserSchema

Creates a user from the given data dictionary.
