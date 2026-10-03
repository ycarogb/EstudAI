from types import SimpleNamespace

import anthropic
import httpx
import openai
import pytest

from app.config import settings
from app.extraction import llm
from app.extraction.llm_config import (
    DEFAULT_MODELS,
    LLMConfig,
    LLMNotConfiguredError,
    config_from_headers,
    reset_request_llm_config,
    set_request_llm_config,
)
from app.main import app


class _ClienteFalso:
    criados: list[dict] = []
    chamadas: list[dict] = []

    def __init__(self, **kwargs):
        _ClienteFalso.criados.append(kwargs)
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._criar))

    async def _criar(self, **kwargs):
        _ClienteFalso.chamadas.append(kwargs)
        mensagem = SimpleNamespace(content="resposta")
        return SimpleNamespace(choices=[SimpleNamespace(message=mensagem)])


class _ClienteAnthropicFalso:
    criados: list[dict] = []
    chamadas: list[dict] = []

    def __init__(self, **kwargs):
        _ClienteAnthropicFalso.criados.append(kwargs)
        self.messages = SimpleNamespace(create=self._criar)

    async def _criar(self, **kwargs):
        _ClienteAnthropicFalso.chamadas.append(kwargs)
        return SimpleNamespace(content=[SimpleNamespace(type="text", text="resposta claude")])


@pytest.fixture
def cliente_falso(monkeypatch):
    _ClienteFalso.criados = []
    _ClienteFalso.chamadas = []
    monkeypatch.setattr(openai, "AsyncOpenAI", _ClienteFalso)
    return _ClienteFalso


@pytest.fixture
def cliente_anthropic_falso(monkeypatch):
    _ClienteAnthropicFalso.criados = []
    _ClienteAnthropicFalso.chamadas = []
    monkeypatch.setattr(anthropic, "AsyncAnthropic", _ClienteAnthropicFalso)
    return _ClienteAnthropicFalso


@pytest.fixture
def servidor_sem_chave(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "openai")
    monkeypatch.setattr(settings, "openai_api_key", "")
    monkeypatch.setattr(settings, "gemini_api_key", "")
    monkeypatch.setattr(settings, "anthropic_api_key", "")
    monkeypatch.setattr(settings, "openrouter_api_key", "")


async def _chamar_com_chave_do_usuario(config: LLMConfig) -> str:
    token = set_request_llm_config(config)
    try:
        return await llm.call_llm("sistema", "usuario")
    finally:
        reset_request_llm_config(token)


@pytest.mark.asyncio
async def test_provedor_gemini_usa_endpoint_e_chave_do_google(monkeypatch, cliente_falso):
    monkeypatch.setattr(settings, "llm_provider", "gemini")
    monkeypatch.setattr(settings, "gemini_api_key", "chave-gemini")
    monkeypatch.setattr(settings, "openai_api_key", "chave-openai")

    resposta = await llm.call_llm("sistema", "usuario")

    assert resposta == "resposta"
    assert cliente_falso.criados[0]["api_key"] == "chave-gemini"
    assert cliente_falso.criados[0]["base_url"] == llm.GEMINI_OPENAI_BASE_URL


@pytest.mark.asyncio
async def test_provedor_openai_usa_endpoint_padrao(monkeypatch, cliente_falso):
    monkeypatch.setattr(settings, "llm_provider", "openai")
    monkeypatch.setattr(settings, "gemini_api_key", "chave-gemini")
    monkeypatch.setattr(settings, "openai_api_key", "chave-openai")

    await llm.call_llm("sistema", "usuario")

    assert cliente_falso.criados[0]["api_key"] == "chave-openai"
    assert cliente_falso.criados[0]["base_url"] is None


def test_modelos_gemini_aceitam_temperature():
    kwargs = llm._openai_chat_kwargs("gemini-3.8-flash", [])
    assert kwargs["temperature"] == 0.2


def test_modelos_de_raciocinio_via_openrouter_nao_recebem_temperature():
    kwargs = llm._openai_chat_kwargs("openai/gpt-5", [])
    assert "temperature" not in kwargs


def test_cabecalhos_completos_geram_configuracao():
    config = config_from_headers({
        "x-llm-provider": "OpenRouter",
        "x-llm-model": "meta-llama/llama-3.3-70b-instruct",
        "x-llm-api-key": " chave-usuario ",
    })

    assert config == LLMConfig("openrouter", "meta-llama/llama-3.3-70b-instruct", "chave-usuario")


def test_cabecalho_sem_modelo_usa_modelo_padrao_do_provedor():
    config = config_from_headers({"x-llm-provider": "anthropic", "x-llm-api-key": "chave"})

    assert config is not None
    assert config.model == DEFAULT_MODELS["anthropic"]


@pytest.mark.parametrize(
    "cabecalhos",
    [
        {},
        {"x-llm-provider": "openai"},
        {"x-llm-api-key": "chave"},
        {"x-llm-provider": "provedor-desconhecido", "x-llm-api-key": "chave"},
    ],
)
def test_cabecalhos_incompletos_ou_invalidos_sao_ignorados(cabecalhos):
    assert config_from_headers(cabecalhos) is None


def test_configuracao_nao_expoe_chave_na_representacao():
    assert "segredo" not in repr(LLMConfig("openai", "gpt-5-mini", "segredo"))


@pytest.mark.asyncio
async def test_chave_do_usuario_tem_prioridade_sobre_a_do_servidor(monkeypatch, cliente_falso):
    monkeypatch.setattr(settings, "llm_provider", "openai")
    monkeypatch.setattr(settings, "openai_api_key", "chave-servidor")

    await _chamar_com_chave_do_usuario(LLMConfig("openrouter", "openrouter/auto", "chave-usuario"))

    assert cliente_falso.criados[0]["api_key"] == "chave-usuario"
    assert cliente_falso.criados[0]["base_url"] == llm.OPENROUTER_BASE_URL
    assert cliente_falso.chamadas[0]["model"] == "openrouter/auto"


@pytest.mark.asyncio
async def test_anthropic_usa_modelo_escolhido_pelo_usuario(
    servidor_sem_chave, cliente_anthropic_falso
):
    resposta = await _chamar_com_chave_do_usuario(
        LLMConfig("anthropic", "claude-haiku-4-5", "chave-claude")
    )

    assert resposta == "resposta claude"
    assert cliente_anthropic_falso.criados[0]["api_key"] == "chave-claude"
    assert cliente_anthropic_falso.chamadas[0]["model"] == "claude-haiku-4-5"
    assert cliente_anthropic_falso.chamadas[0]["system"] == "sistema"


@pytest.mark.asyncio
async def test_sem_chave_configurada_lanca_erro_claro(servidor_sem_chave):
    with pytest.raises(LLMNotConfiguredError, match="Configurar IA"):
        await llm.call_llm("sistema", "usuario")


def _cliente_http() -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://teste")


@pytest.mark.asyncio
async def test_status_informa_ausencia_de_chave_no_servidor(servidor_sem_chave):
    async with _cliente_http() as cliente:
        resposta = await cliente.get("/api/llm/status")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["server_configured"] is False
    assert corpo["default_models"] == DEFAULT_MODELS


@pytest.mark.asyncio
async def test_status_nao_expoe_chave_do_servidor(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "openai")
    monkeypatch.setattr(settings, "openai_api_key", "chave-secreta-servidor")

    async with _cliente_http() as cliente:
        resposta = await cliente.get("/api/llm/status")

    assert resposta.json()["server_configured"] is True
    assert "chave-secreta-servidor" not in resposta.text


@pytest.mark.asyncio
async def test_teste_de_conexao_usa_chave_enviada_nos_cabecalhos(servidor_sem_chave, cliente_falso):
    async with _cliente_http() as cliente:
        resposta = await cliente.post(
            "/api/llm/test",
            headers={
                "X-LLM-Provider": "gemini",
                "X-LLM-Model": "gemini-3.8-flash",
                "X-LLM-Api-Key": "chave-do-navegador",
            },
        )

    assert resposta.status_code == 200
    assert resposta.json() == {"ok": True, "provider": "gemini", "model": "gemini-3.8-flash"}
    assert cliente_falso.criados[0]["api_key"] == "chave-do-navegador"


class _ErroDoProvedor(Exception):
    def __init__(self, status_code: int):
        super().__init__(f"Error code: {status_code}")
        self.status_code = status_code


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status_code", "mensagem_esperada"),
    [
        (401, "Chave de API inválida"),
        (404, "Modelo não encontrado"),
        (429, "créditos esgotados"),
    ],
)
async def test_teste_de_conexao_traduz_erros_do_provedor(
    monkeypatch, servidor_sem_chave, status_code, mensagem_esperada
):
    async def falhar(*_args, **_kwargs):
        raise _ErroDoProvedor(status_code)

    monkeypatch.setattr(llm, "_call_openai_compatible", falhar)

    async with _cliente_http() as cliente:
        resposta = await cliente.post(
            "/api/llm/test",
            headers={"X-LLM-Provider": "openai", "X-LLM-Api-Key": "chave-qualquer"},
        )

    assert resposta.status_code == 400
    assert mensagem_esperada in resposta.json()["detail"]


@pytest.mark.asyncio
async def test_analise_de_pdfs_sem_chave_retorna_400(servidor_sem_chave):
    async with _cliente_http() as cliente:
        resposta = await cliente.post(
            "/api/analyze-pdfs",
            files={"files": ("artigo.pdf", b"%PDF-1.4", "application/pdf")},
        )

    assert resposta.status_code == 400
    assert resposta.json()["code"] == "llm_not_configured"
    assert "Configurar IA" in resposta.json()["detail"]
