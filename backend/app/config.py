"""ORCA backend settings. LLM provider is swappable via env; never hardcode.

Supported LLM_PROVIDER values (config-only in Phase 0; wiring in Phase 3):
  mock (offline default), groq, openai, openai-compatible, anthropic, ollama.
Groq hosts GPT-OSS as OpenAI-compatible API, e.g. model `openai/gpt-oss-120b`
at base URL `https://api.groq.com/openai/v1` (verify in Phase 3).
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ORCA_", env_file=".env")

    LLM_PROVIDER: str = "mock"
    LLM_MODEL: str = ""
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = ""
    LOG_LEVEL: str = "INFO"
    DATA_CACHE_DIR: str = "data/cache"
    DATA_FIXTURES_DIR: str = "data/fixtures"

    def resolved_llm(self) -> tuple[str, str, str]:
        """Return (provider, model, base_url) with Groq defaults applied."""
        provider = self.LLM_PROVIDER.strip().lower() or "mock"
        model = self.LLM_MODEL.strip()
        base_url = self.LLM_BASE_URL.strip()
        if provider == "groq":
            model = model or "openai/gpt-oss-120b"
            base_url = base_url or "https://api.groq.com/openai/v1"
        return provider, model, base_url


settings = Settings()
