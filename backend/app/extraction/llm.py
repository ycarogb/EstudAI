import json
import logging
import re

import httpx

from app.config import settings
from app.extraction.llm_config import (
    LLMConfig,
    LLMNotConfiguredError,
    current_llm_config,
    ollama_configured,
)

logger = logging.getLogger(__name__)

MAX_TEXT_LENGTH = 12000
ANTHROPIC_MAX_TOKENS = 8000

GEMINI_OPENAI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# URLs fixas: o usuário escolhe o provedor, nunca o endereço (evita SSRF).
OPENAI_COMPATIBLE_BASE_URLS: dict[str, str | None] = {
    "openai": None,
    "gemini": GEMINI_OPENAI_BASE_URL,
    "openrouter": OPENROUTER_BASE_URL,
}


async def fetch_pdf_text(url: str) -> str | None:
    if url.startswith("local://"):
        return None
    try:
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "")
            if "pdf" not in content_type and not url.lower().endswith(".pdf"):
                return None

            import fitz

            doc = fitz.open(stream=resp.content, filetype="pdf")
            text_parts = []
            for page in doc:
                text_parts.append(page.get_text())
            doc.close()
            return "\n".join(text_parts)[:MAX_TEXT_LENGTH]
    except Exception as e:
        logger.warning("PDF fetch failed for %s: %s", url, e)
        return None


def get_source_text(paper_abstract: str | None, pdf_text: str | None) -> str:
    if pdf_text and len(pdf_text.strip()) > 200:
        return pdf_text[:MAX_TEXT_LENGTH]
    if paper_abstract:
        return paper_abstract
    return ""


def _openai_chat_kwargs(model: str, messages: list[dict]) -> dict:
    """Monta kwargs compatíveis com o modelo (gpt-5/o-series não aceitam temperature customizado)."""
    kwargs: dict = {"model": model, "messages": messages}
    restricted = ("gpt-5", "o1", "o3", "o4")
    model_name = model.split("/")[-1]
    if not any(model_name.startswith(prefix) for prefix in restricted):
        kwargs["temperature"] = 0.2
    return kwargs


async def _call_openai_compatible(config: LLMConfig, system: str, user: str) -> str:
    from openai import AsyncOpenAI

    # Retentativas extras absorvem os erros 429 frequentes nas camadas gratuitas.
    client = AsyncOpenAI(
        api_key=config.api_key,
        base_url=OPENAI_COMPATIBLE_BASE_URLS[config.provider],
        timeout=settings.llm_timeout_seconds,
        max_retries=5,
    )
    resp = await client.chat.completions.create(
        **_openai_chat_kwargs(
            config.model,
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
    )
    return resp.choices[0].message.content or ""


async def _call_anthropic(config: LLMConfig, system: str, user: str) -> str:
    import anthropic

    client = anthropic.AsyncAnthropic(
        api_key=config.api_key,
        timeout=settings.llm_timeout_seconds,
        max_retries=5,
    )
    resp = await client.messages.create(
        model=config.model,
        max_tokens=ANTHROPIC_MAX_TOKENS,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return "".join(block.text for block in resp.content if block.type == "text")


async def _call_ollama(system: str, user: str) -> str:
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{settings.ollama_base_url}/api/chat",
            json={
                "model": "llama3.2",
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "stream": False,
            },
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"]


async def call_llm(system: str, user: str) -> str:
    config = current_llm_config()
    if config is None:
        if ollama_configured():
            return await _call_ollama(system, user)
        raise LLMNotConfiguredError()

    if config.provider == "anthropic":
        return await _call_anthropic(config, system, user)
    return await _call_openai_compatible(config, system, user)


def parse_extraction_response(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "objectives": raw[:500],
            "results": "",
            "gaps": "",
            "citations": [],
        }
