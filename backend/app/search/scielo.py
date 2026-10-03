import re

import httpx

from app.models.schemas import Paper, PaperSource, SearchFilters
from app.search.base import make_paper_id

# Membros do Crossref que registram os DOIs das coleções SciELO
# (Brasil/FapUNIFESP, Espanha e Chile). O buscador search.scielo.org
# bloqueia acesso automatizado, por isso a busca usa o Crossref.
SCIELO_CROSSREF_MEMBERS = ("530", "2868", "2516")


def _clean_abstract(raw: str | None) -> str | None:
    if not raw:
        return None
    text = re.sub(r"<[^>]+>", " ", raw)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


class SciELOAdapter:
    name = "scielo"
    BASE_URL = "https://api.crossref.org/works"
    SELECT_FIELDS = "DOI,title,author,issued,abstract,container-title,URL,link,type"

    def _headers(self) -> dict[str, str]:
        return {"User-Agent": "EstudAI/1.0 (mailto:estudai@research.br)"}

    def _parse_item(self, item: dict) -> Paper:
        doi = item.get("DOI") or ""

        titles = item.get("title") or []
        title = titles[0] if titles else "Sem título"

        authors = []
        for author in item.get("author", []):
            name = " ".join(p for p in (author.get("given"), author.get("family")) if p)
            if name:
                authors.append(name)

        year = None
        date_parts = (item.get("issued") or {}).get("date-parts") or [[]]
        if date_parts and date_parts[0] and date_parts[0][0]:
            year = int(date_parts[0][0])

        pdf_url = next(
            (
                link.get("URL")
                for link in item.get("link", [])
                if link.get("URL", "").lower().endswith(".pdf")
                or link.get("content-type") == "application/pdf"
            ),
            None,
        )

        return Paper(
            id=make_paper_id("scielo", doi or title),
            source=PaperSource.SCIELO,
            title=title,
            authors=authors,
            year=year,
            abstract=_clean_abstract(item.get("abstract")),
            doi=doi or None,
            url=f"https://doi.org/{doi}" if doi else item.get("URL"),
            pdf_url=pdf_url,
            keywords=[],
            document_type=item.get("type"),
        )

    def _build_filter(self, filters: SearchFilters) -> str:
        parts = [f"member:{member}" for member in SCIELO_CROSSREF_MEMBERS]
        if filters.year_from:
            parts.append(f"from-pub-date:{filters.year_from}")
        if filters.year_to:
            parts.append(f"until-pub-date:{filters.year_to}")
        return ",".join(parts)

    async def search(self, query: str, filters: SearchFilters) -> list[Paper]:
        params: dict[str, str | int] = {
            "query.bibliographic": query,
            "filter": self._build_filter(filters),
            "rows": min(filters.limit, 50),
            "select": self.SELECT_FIELDS,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(self.BASE_URL, params=params, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()

        items = data.get("message", {}).get("items", [])
        return [self._parse_item(item) for item in items]

    async def get_by_id(self, paper_id: str) -> Paper | None:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{self.BASE_URL}/{paper_id}", headers=self._headers())
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return self._parse_item(resp.json().get("message", {}))
