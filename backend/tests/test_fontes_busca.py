import httpx
import pytest

from app.config import settings
from app.models.schemas import Paper, PaperSource, SearchFilters
from app.search import google_scholar, scielo
from app.search.google_scholar import GoogleScholarAdapter
from app.search.hub import DEFAULT_SOURCES, SearchHub
from app.search.scielo import SciELOAdapter

CHAVE_SERPAPI = "chave-serpapi-secreta"

ITEM_CROSSREF_SCIELO = {
    "DOI": "10.1590/1806-9126-rbef-2018-0309",
    "title": ["Gamificação como estratégia de aprendizagem ativa no ensino de Física"],
    "author": [
        {"given": "João Batista da", "family": "Silva"},
        {"given": "Gilvandenys Leite", "family": "Sales"},
    ],
    "issued": {"date-parts": [[2019]]},
    "abstract": "<jats:p>Resumo   Neste trabalho\n são apresentados os resultados.</jats:p>",
    "link": [
        {
            "URL": "http://www.scielo.br/pdf/rbef/v41n4/1806-9126-RBEF-41-4-e20180309.pdf",
            "content-type": "unspecified",
        }
    ],
    "type": "journal-article",
}

RESULTADO_SERPAPI = {
    "result_id": "abc123",
    "title": "Metodologias ativas no ensino superior",
    "link": "https://www.scielo.br/j/ep/a/10.1590/s1517-9702202248240123/",
    "snippet": "Este estudo analisa o uso de metodologias ativas…",
    "publication_info": {
        "summary": "M Souza, A Lima - Educação e Pesquisa, 2022 - SciELO Brasil",
        "authors": [{"name": "M Souza"}, {"name": "A Lima"}],
    },
    "resources": [{"title": "scielo.br", "file_format": "PDF", "link": "https://www.scielo.br/doc.pdf"}],
}


def _cliente_com_transporte(monkeypatch, modulo, handler):
    cliente_real = httpx.AsyncClient

    def fabrica(*args, **kwargs):
        return cliente_real(*args, transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(modulo.httpx, "AsyncClient", fabrica)


def test_buscas_padrao_incluem_scielo_e_google_scholar():
    assert PaperSource.SCIELO in DEFAULT_SOURCES
    assert PaperSource.GOOGLE_SCHOLAR in DEFAULT_SOURCES


class _AdaptadorFalso:
    def __init__(self, nome: str, papers: list[Paper]) -> None:
        self.name = nome
        self._papers = papers

    async def search(self, query: str, filters: SearchFilters) -> list[Paper]:
        return [paper.model_copy() for paper in self._papers]

    async def get_by_id(self, paper_id: str) -> Paper | None:
        return None


@pytest.mark.asyncio
async def test_artigo_scielo_tambem_indexado_no_openalex_aparece_como_scielo():
    doi = "10.1590/s1414-40772021000300005"
    hub = SearchHub()
    hub._adapters = {
        PaperSource.OPENALEX: _AdaptadorFalso(
            "openalex",
            [Paper(id="oa", source=PaperSource.OPENALEX, title="Inovação no ensino", doi=doi, keywords=["Educação"])],
        ),
        PaperSource.SCIELO: _AdaptadorFalso(
            "scielo",
            [Paper(id="sc", source=PaperSource.SCIELO, title="Inovação no ensino", doi=doi, pdf_url="https://scielo.br/a.pdf")],
        ),
    }

    papers = await hub.search("inovação no ensino")

    assert len(papers) == 1
    assert papers[0].source == PaperSource.SCIELO
    assert papers[0].pdf_url == "https://scielo.br/a.pdf"


def test_scielo_converte_item_do_crossref():
    paper = SciELOAdapter()._parse_item(ITEM_CROSSREF_SCIELO)

    assert paper.source == PaperSource.SCIELO
    assert paper.title.startswith("Gamificação")
    assert paper.authors == ["João Batista da Silva", "Gilvandenys Leite Sales"]
    assert paper.year == 2019
    assert paper.abstract == "Resumo Neste trabalho são apresentados os resultados."
    assert paper.doi == "10.1590/1806-9126-rbef-2018-0309"
    assert paper.url == "https://doi.org/10.1590/1806-9126-rbef-2018-0309"
    assert paper.pdf_url.endswith(".pdf")


@pytest.mark.asyncio
async def test_scielo_restringe_busca_aos_membros_scielo_e_ao_periodo(monkeypatch):
    requisicoes: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requisicoes.append(request)
        return httpx.Response(200, json={"message": {"items": [ITEM_CROSSREF_SCIELO]}})

    _cliente_com_transporte(monkeypatch, scielo, handler)

    papers = await SciELOAdapter().search(
        "aprendizagem ativa", SearchFilters(year_from=2018, year_to=2024, limit=10)
    )

    filtro = requisicoes[0].url.params["filter"]
    assert "member:530" in filtro
    assert "from-pub-date:2018" in filtro
    assert "until-pub-date:2024" in filtro
    assert requisicoes[0].url.params["rows"] == "10"
    assert len(papers) == 1


@pytest.mark.asyncio
async def test_google_scholar_sem_chave_nao_faz_requisicao(monkeypatch):
    monkeypatch.setattr(settings, "serpapi_api_key", "")

    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("Não deveria chamar a SerpApi sem chave")

    _cliente_com_transporte(monkeypatch, google_scholar, handler)

    assert await GoogleScholarAdapter().search("tema", SearchFilters()) == []


def test_google_scholar_converte_resultado_da_serpapi():
    paper = GoogleScholarAdapter()._parse_result(RESULTADO_SERPAPI)

    assert paper.source == PaperSource.GOOGLE_SCHOLAR
    assert paper.authors == ["M Souza", "A Lima"]
    assert paper.year == 2022
    assert paper.doi == "10.1590/s1517-9702202248240123"
    assert paper.pdf_url == "https://www.scielo.br/doc.pdf"
    assert paper.abstract.startswith("Este estudo")


def test_google_scholar_extrai_autores_do_resumo_quando_ausentes():
    resultado = {
        "title": "Trabalho",
        "publication_info": {"summary": "J Pereira, C Alves - Revista X, 2015 - exemplo.org"},
    }

    paper = GoogleScholarAdapter()._parse_result(resultado)

    assert paper.authors == ["J Pereira", "C Alves"]
    assert paper.year == 2015


@pytest.mark.asyncio
async def test_google_scholar_envia_periodo_e_le_resultados(monkeypatch):
    monkeypatch.setattr(settings, "serpapi_api_key", CHAVE_SERPAPI)
    requisicoes: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requisicoes.append(request)
        return httpx.Response(200, json={"organic_results": [RESULTADO_SERPAPI]})

    _cliente_com_transporte(monkeypatch, google_scholar, handler)

    papers = await GoogleScholarAdapter().search("tema", SearchFilters(year_from=2020, year_to=2023, limit=50))

    params = requisicoes[0].url.params
    assert params["engine"] == "google_scholar"
    assert params["as_ylo"] == "2020"
    assert params["as_yhi"] == "2023"
    assert params["num"] == "20"
    assert len(papers) == 1


@pytest.mark.asyncio
async def test_google_scholar_sem_resultados_retorna_lista_vazia(monkeypatch):
    monkeypatch.setattr(settings, "serpapi_api_key", CHAVE_SERPAPI)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"error": "Google hasn't returned any results for this query."})

    _cliente_com_transporte(monkeypatch, google_scholar, handler)

    assert await GoogleScholarAdapter().search("tema", SearchFilters()) == []


@pytest.mark.asyncio
async def test_google_scholar_erro_http_nao_expoe_a_chave(monkeypatch):
    monkeypatch.setattr(settings, "serpapi_api_key", CHAVE_SERPAPI)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "Invalid API key."})

    _cliente_com_transporte(monkeypatch, google_scholar, handler)

    with pytest.raises(RuntimeError) as erro:
        await GoogleScholarAdapter().search("tema", SearchFilters())

    assert "401" in str(erro.value)
    assert CHAVE_SERPAPI not in str(erro.value)


@pytest.mark.asyncio
async def test_google_scholar_falha_de_conexao_nao_expoe_a_chave(monkeypatch):
    monkeypatch.setattr(settings, "serpapi_api_key", CHAVE_SERPAPI)

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(f"falha ao conectar em {request.url}", request=request)

    _cliente_com_transporte(monkeypatch, google_scholar, handler)

    with pytest.raises(RuntimeError) as erro:
        await GoogleScholarAdapter().search("tema", SearchFilters())

    assert CHAVE_SERPAPI not in str(erro.value)
    assert erro.value.__cause__ is None
