from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Core settings
    PROJECT_NAME: str = "Med-Core Intake API"
    ENVIRONMENT: str = "local"
    
    # Database Credentials
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str 
    POSTGRES_PORT: int 
    
    # Computed async DB URL
    @property
    def ASYNC_DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Security Stubs
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    # Cryptographic Key for PHI Application-Level Encryption
    ENCRYPTION_KEY: str

    # Caching / Rate Limiting
    REDIS_URL: str

    # The Sandbox
    TEST_DATABASE_URL: str

    # Strictly enforce reading from .env
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    

# Global singleton
settings = Settings() # type: ignore
