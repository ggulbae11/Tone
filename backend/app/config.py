from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Tone Analyzer API"
    app_env: str = "development"
    database_url: str = "sqlite:///./tone.db"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    llm_provider: str = "disabled"
    llm_api_key: str | None = None
    llm_model: str = "gemini-2.5-flash-lite"
    llm_fallback_models: str = "gemini-2.0-flash"
    llm_max_retries: int = 0
    llm_timeout_seconds: float = 6.0

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()