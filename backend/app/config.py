from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    database_url: str = "sqlite+aiosqlite:///./estudai.db"
    cors_origins: str = (
        "http://localhost:3000,http://localhost:3001,"
        "http://127.0.0.1:3000,http://127.0.0.1:3001"
    )

    openai_api_key: str = ""
    gemini_api_key: str = ""
    anthropic_api_key: str = ""
    openrouter_api_key: str = ""
    ollama_base_url: str = ""
    llm_provider: str = "openai"
    llm_model: str = "gpt-5"
    llm_timeout_seconds: float = 180.0

    openalex_email: str = ""
    semantic_scholar_api_key: str = ""
    serpapi_api_key: str = ""

    scopus_api_key: str = ""
    scopus_inst_token: str = ""
    wos_api_key: str = ""

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
