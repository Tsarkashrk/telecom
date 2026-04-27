from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = ""
    # vul: database_url: str = "postgresql://postgres:password@localhost/telecom_db"
    # vul: secret_key: str = "super-secret-for-prod"
    secret_key: str = ""
    internal_api_key: str | None = None
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
        return self.database_url.startswith("postgresql")


settings = Settings()
