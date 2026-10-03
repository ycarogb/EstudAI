import httpx

from app.config import settings
from app.models.schemas import Paper, PaperSource, SearchFilters
from app.search.base import make_paper_id


class OpenAlexAdapter:
    name = "openalex"
    BASE_URL = "https://api.openalex.org/works"

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Accept": "application/json"}
        if settings.openalex_email:
            headers["User-Agent"] = f"EstudAI/1.0 (mailto:{settings.openalex_email})"
        return headers

    def _parse_work(self, work: dict) -> Paper:
        doi = work.get("doi", "")
        if doi and doi.startswith("https://doi.org/"):
            doi = doi.replace("https://doi.org/", "")

        authors = []
        for authorship in work.get("authorships", []):
            author = authorship.get("author", {})
            if name := author.get("display_name"):
                authors.append(name)

        abstract = None
        if inv := work.get("abstract_inverted_index"):
            words: list[tuple[int, str]] = []
            for word, positions in inv.items():
                for pos in positions:
                    words.append((pos, word))
            words.sort()
            abstract = " ".join(w for _, w in words)

        year = work.get("publication_year")
        open_access = work.get("open_access", {})
        pdf_url = open_access.get("oa_url")

        primary_loc = work.get("primary_location", {}) or {}
        url = primary_loc.get("landing_page_url") or work.get("id")

        return Paper(
            id=make_paper_id("openalex", work.get("id", "")),
            source=PaperSource.OPENALEX,
            title=work.get("display_name") or work.get("title", "Sem título"),
            authors=authors,
            year=year,
            abstract=abstract,
            doi=doi or None,
            url=url,
            pdf_url=pdf_url,
            keywords=[c.get("display_name", "") for c in work.get("concepts", [])[:5] if c.get("display_name")],
            document_type=work.get("type"),
        )

    async def search(self, query: str, filters: SearchFilters) -> list[Paper]:
        params: dict[str, str | int] = {
            "search": query,
            "per_page": min(filters.limit, 50),
            "sort": "relevance_score:desc",
        }
        filter_parts = []
        if filters.year_from:
            filter_parts.append(f"publication_year:>{filters.year_from - 1}")
        if filters.year_to:
            filter_parts.append(f"publication_year:<{filters.year_to + 1}")
        if filter_parts:
            params["filter"] = ",".join(filter_parts)

        if settings.openalex_email:
            params["mailto"] = settings.openalex_email

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(self.BASE_URL, params=params, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()

        return [self._parse_work(w) for w in data.get("results", [])]

    async def get_by_id(self, paper_id: str) -> Paper | None:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{self.BASE_URL}/{paper_id}", headers=self._headers())
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return self._parse_work(resp.json())
