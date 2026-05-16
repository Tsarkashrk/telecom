from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


PLACEHOLDER_HASH = "__migrated_to_user_credentials__"


def migrate_user_passwords(engine: Engine) -> None:
    inspector = inspect(engine)

    if not inspector.has_table("users") or not inspector.has_table("user_credentials"):
        return

    user_columns = {column["name"] for column in inspector.get_columns("users")}
    if "hashed_password" not in user_columns:
        return

    credential_columns = {
        column["name"] for column in inspector.get_columns("user_credentials")
    }
    if "user_id" not in credential_columns or "hashed_password" not in credential_columns:
        return

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO user_credentials (user_id, hashed_password, password_updated_at, created_at)
                SELECT users.id, users.hashed_password, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                FROM users
                LEFT JOIN user_credentials
                    ON user_credentials.user_id = users.id
                WHERE user_credentials.user_id IS NULL
                  AND users.hashed_password IS NOT NULL
                  AND users.hashed_password != ''
                  AND users.hashed_password != :placeholder
                """
            ),
            {"placeholder": PLACEHOLDER_HASH},
        )
        connection.execute(
            text(
                """
                UPDATE users
                SET hashed_password = :placeholder
                WHERE hashed_password IS NOT NULL
                  AND hashed_password != :placeholder
                """
            ),
            {"placeholder": PLACEHOLDER_HASH},
        )

        dialect_name = engine.dialect.name
        if dialect_name == "postgresql":
            connection.execute(
                text(
                    f"""
                    ALTER TABLE users
                    ALTER COLUMN hashed_password SET DEFAULT '{PLACEHOLDER_HASH}'
                    """
                )
            )
        elif dialect_name == "sqlite":
            # SQLite не умеет ALTER COLUMN SET DEFAULT в совместимом виде;
            # ORM default покрывает новые вставки для тестового окружения.
            pass
