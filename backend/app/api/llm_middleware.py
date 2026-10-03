from starlette.types import ASGIApp, Receive, Scope, Send

from app.extraction.llm_config import (
    config_from_headers,
    reset_request_llm_config,
    set_request_llm_config,
)


class LLMConfigMiddleware:
    """
    Disponibiliza a chave de IA enviada pelo usuário durante toda a requisição,
    inclusive respostas em streaming (SSE). A chave nunca é persistida nem registrada.
    """

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = {
            name.decode("latin-1").lower(): value.decode("latin-1")
            for name, value in scope["headers"]
        }
        token = set_request_llm_config(config_from_headers(headers))
        try:
            await self.app(scope, receive, send)
        finally:
            reset_request_llm_config(token)
