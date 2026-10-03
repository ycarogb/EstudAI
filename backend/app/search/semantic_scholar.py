import httpx

from app.config import settings
from app.models.schemas import Paper, PaperSource, SearchFilters
from app.search.base import make_paper_id


class SemanticScholarAdapter:
    name = "semantic_scholar"
    BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search"

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if settings.semantic_scholar_api_key:
            headers["x-api-key"] = settings.semantic_scholar_api_key
        return headers

    def _parse_paper(self, item: dict) -> Paper:
        external_ids = item.get("externalIds") or {}
        doi = external_ids.get("DOI")

        authors = [a.get("name", "") for a in item.get("authors", []) if a.get("name")]

        open_access = item.get("openAccessPdf") or {}
        pdf_url = open_access.get("url")

        year = item.get("year")
        if year_from_pub := item.get("publicationDate"):
            try:
                year = int(year_from_pub[:4])
            except (ValueError, TypeError):
                pass

        return Paper(
            id=make_paper_id("semantic_scholar", item.get("paperId", "")),
            source=PaperSource.SEMANTIC_SCHOLAR,
            title=item.get("title") or "Sem título",
            authors=authors,
            year=year,
            abstract=item.get("abstract"),
            doi=doi,
            url=item.get("url"),
            pdf_url=pdf_url,
            keywords=[],
            document_type=None,
        )

    async def search(self, query: str, filters: SearchFilters) -> list[Paper]:
        params: dict[str, str | int] = {
            "query": query,
            "limit": min(filters.limit, 50),
            "fields": "paperId,title,abstract,year,authors,externalIds,url,openAccessPdf,publicationDate",
        }

        if filters.year_from:
            params["year"] = f"{filters.year_from}-"

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(self.BASE_URL, params=params, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()

        papers = [self._parse_paper(p) for p in data.get("data", [])]

        if filters.year_to:
            papers = [p for p in papers if p.year is None or p.year <= filters.year_to]

        return papers

    async def get_by_id(self, paper_id: str) -> Paper | None:
        fields = "paperId,title,abstract,year,authors,externalIds,url,openAccessPdf,publicationDate"
        url = f"https://api.semanticscholar.org/graph/v1/paper/{paper_id}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, params={"fields": fields}, headers=self._headers())
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return self._parse_paper(resp.json())
