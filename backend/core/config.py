from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    DATABASE_URL: str = "sqlite:///./salescoach.db"

    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2"

    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    WHISPER_MODEL_SIZE: str = "tiny"
    WHISPER_DEVICE: str = "cpu"

    AUDIO_SAMPLE_RATE: int = 16000
    AUDIO_CHANNELS: int = 1
    AUDIO_CHUNK_SIZE: int = 1024

    RECORDINGS_DIR: str = "./recordings"

    @property
    def database_url(self) -> str:
        return self.DATABASE_URL

    @property
    def async_database_url(self) -> str:
        return self.DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
