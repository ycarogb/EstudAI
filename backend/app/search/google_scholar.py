import re

import httpx

from app.config import settings
from app.models.schemas import Paper, PaperSource, SearchFilters
from app.search.base import make_paper_id

YEAR_PATTERN = re.compile(r"\b(19|20)\d{2}\b")
DOI_PATTERN = re.compile(r"10\.\d{4,9}/[^\s?#&]+")
NO_RESULTS_ERROR = "hasn't returned any results"


class GoogleScholarAdapter:
    """Google Scholar não tem API oficial; a busca usa a SerpApi (SERPAPI_API_KEY)."""

    name = "google_scholar"
    BASE_URL = "https://serpapi.com/search.json"
    MAX_RESULTS = 20

    def _is_configured(self) -> bool:
        return bool(settings.serpapi_api_key)

    def _parse_result(self, item: dict) -> Paper:
        info = item.get("publication_info") or {}
        summary = info.get("summary") or ""

        authors = [a["name"] for a in info.get("authors", []) if a.get("name")]
        if not authors and " - " in summary:
            authors = [name.strip() for name in summary.split(" - ")[0].split(",") if name.strip()]

        year_match = YEAR_PATTERN.search(summary)
        link = item.get("link")
        doi_match = DOI_PATTERN.search(link or "")

        pdf_url = next(
            (r.get("link") for r in item.get("resources", []) if r.get("file_format") == "PDF"),
            None,
        )

        return Paper(
            id=make_paper_id("google_scholar", item.get("result_id") or item.get("title", "")),
            source=PaperSource.GOOGLE_SCHOLAR,
            title=item.get("title") or "Sem título",
            authors=authors,
            year=int(year_match.group(0)) if year_match else None,
            abstract=item.get("snippet"),
            doi=doi_match.group(0).rstrip("/.") if doi_match else None,
            url=link,
            pdf_url=pdf_url,
            keywords=[],
            document_type=item.get("type"),
        )

    async def _fetch(self, params: dict[str, str | int]) -> dict:
        # A chave vai na query string; erros do httpx citam a URL e não podem ser propagados.
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(self.BASE_URL, params=params)
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Falha de conexão com a SerpApi ({type(exc).__name__})") from None

        data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
        error = data.get("error")
        if error and NO_RESULTS_ERROR in error:
            return {}
        if resp.status_code != 200 or error:
            raise RuntimeError(f"SerpApi respondeu {resp.status_code}: {error or 'erro desconhecido'}")
        return data

    async def search(self, query: str, filters: SearchFilters) -> list[Paper]:
        if not self._is_configured():
            return []

        params: dict[str, str | int] = {
            "engine": "google_scholar",
            "q": query,
            "num": min(filters.limit, self.MAX_RESULTS),
            "api_key": settings.serpapi_api_key,
        }
        if filters.year_from:
            params["as_ylo"] = filters.year_from
        if filters.year_to:
            params["as_yhi"] = filters.year_to

        data = await self._fetch(params)
        return [self._parse_result(item) for item in data.get("organic_results", [])]

    async def get_by_id(self, paper_id: str) -> Paper | None:
        return None
