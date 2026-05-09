from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    PROJECT_NAME: str = "Med-Core Intake DevSecOps API"
    ENVIRONMENT: str = "local"

    # Database
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int

    # Connection pool (overridable via env)
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Security
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    # Encryption (single key, version 1)
    ENCRYPTION_KEY: str

    # CORS – comma‑separated origins
    ALLOWED_ORIGINS: str = "http://localhost:3000"

    @property
    def ALLOWED_ORIGINS_LIST(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

    # Redis
    REDIS_URL: str

    # Test
    TEST_DATABASE_URL: str

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()  # type: ignore