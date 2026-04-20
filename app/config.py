import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Параметры приложения из переменных окружения"""
    
    database_url: str = "postgresql://postgres:password@localhost/telecom_db"
    secret_key: str = "change-me-in-production"
    internal_api_key: str = ""
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    log_level: str = "INFO"
    debug: bool = False
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    @property
    def is_postgres(self) -> bool:
        """Проверка использования PostgreSQL"""
        return self.database_url.startswith("postgresql")


settings = Settings()
