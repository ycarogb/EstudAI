"""
Resolução da configuração de LLM por requisição.

A chave pode vir do usuário (cabeçalhos HTTP, nunca persistida) ou do servidor (.env).
A chave do usuário tem prioridade.
"""

from contextvars import ContextVar, Token
from dataclasses import dataclass, field

from app.config import settings

SUPPORTED_PROVIDERS = ("openai", "gemini", "anthropic", "openrouter")

DEFAULT_MODELS = {
    "openai": "gpt-5-mini",
    "gemini": "gemini-3.8-flash",
    "anthropic": "claude-sonnet-5",
    "openrouter": "openrouter/auto",
}

HEADER_PROVIDER = "x-llm-provider"
HEADER_MODEL = "x-llm-model"
HEADER_API_KEY = "x-llm-api-key"

LLM_NOT_CONFIGURED_MESSAGE = (
    "Nenhuma chave de IA configurada. Clique em 'Configurar IA' e informe a chave "
    "do provedor que você usa (OpenAI, Gemini, Claude ou OpenRouter)."
)


class LLMNotConfiguredError(Exception):
    def __init__(self, message: str = LLM_NOT_CONFIGURED_MESSAGE):
        super().__init__(message)


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    model: str
    api_key: str = field(repr=False)


_request_config: ContextVar[LLMConfig | None] = ContextVar("request_llm_config", default=None)


def config_from_headers(headers: dict[str, str]) -> LLMConfig | None:
    provider = headers.get(HEADER_PROVIDER, "").strip().lower()
    api_key = headers.get(HEADER_API_KEY, "").strip()
    if provider not in SUPPORTED_PROVIDERS or not api_key:
        return None
    model = headers.get(HEADER_MODEL, "").strip() or DEFAULT_MODELS[provider]
    return LLMConfig(provider=provider, model=model, api_key=api_key)


def server_llm_config() -> LLMConfig | None:
    provider = settings.llm_provider.lower()
    keys = {
        "openai": settings.openai_api_key,
        "gemini": settings.gemini_api_key,
        "anthropic": settings.anthropic_api_key,
        "openrouter": settings.openrouter_api_key,
    }
    api_key = keys.get(provider, "")
    if not api_key:
        return None
    return LLMConfig(
        provider=provider,
        model=settings.llm_model or DEFAULT_MODELS[provider],
        api_key=api_key,
    )


def ollama_configured() -> bool:
    return settings.llm_provider.lower() == "ollama" and bool(settings.ollama_base_url)


def set_request_llm_config(config: LLMConfig | None) -> Token:
    return _request_config.set(config)


def reset_request_llm_config(token: Token) -> None:
    _request_config.reset(token)


def current_llm_config() -> LLMConfig | None:
    return _request_config.get() or server_llm_config()


def is_llm_configured() -> bool:
    return current_llm_config() is not None or ollama_configured()
