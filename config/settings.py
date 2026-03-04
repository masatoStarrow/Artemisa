"""
Application settings using pydantic-settings.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    db_name: str = "crm_users_db"
    db_user: str = "postgres"
    db_password: str = "postgres"
    db_host: str = "db"
    db_port: int = 5432
    db_pool_size: int = 10
    db_max_overflow: int = 20
    app_env: str = "local"
    app_port: int = 8001
    log_level: str = "INFO"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
