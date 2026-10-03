import httpx

from app.models.schemas import Paper, PaperSource, SearchFilters
from app.search.base import make_paper_id


class BDTDAdapter:
    name = "bdtd"
    BASE_URL = "https://bdtd.ibict.br/vufind/api/v1/search"
    RECORD_URL = "https://bdtd.ibict.br/vufind/api/v1/record"

    def _parse_record(self, record: dict) -> Paper:
        record_id = record.get("id", "")
        title = record.get("title", ["Sem título"])
        if isinstance(title, list):
            title = title[0] if title else "Sem título"

        authors = record.get("author", [])
        if isinstance(authors, str):
            authors = [authors]

        year = None
        publish_date = record.get("publishDate", [])
        if isinstance(publish_date, list) and publish_date:
            try:
                year = int(str(publish_date[0])[:4])
            except (ValueError, TypeError):
                pass
        elif isinstance(publish_date, str):
            try:
                year = int(publish_date[:4])
            except (ValueError, TypeError):
                pass

        abstract = record.get("description", [])
        if isinstance(abstract, list):
            abstract = " ".join(abstract) if abstract else None
        elif not abstract:
            abstract = None

        url_list = record.get("url", [])
        url = url_list[0] if isinstance(url_list, list) and url_list else f"https://bdtd.ibict.br/vufind/Record/{record_id}"

        doc_type = record.get("format", [])
        if isinstance(doc_type, list):
            doc_type = doc_type[0] if doc_type else "tese/dissertação"

        return Paper(
            id=make_paper_id("bdtd", record_id),
            source=PaperSource.BDTD,
            title=title,
            authors=authors,
            year=year,
            abstract=abstract,
            doi=None,
            url=url,
            pdf_url=url,
            keywords=[],
            document_type=doc_type,
        )

    async def search(self, query: str, filters: SearchFilters) -> list[Paper]:
        params: dict[str, str | int] = {
            "lookfor": query,
            "type": "AllFields",
            "limit": min(filters.limit, 50),
            "page": 1,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(self.BASE_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

        records = data.get("records", data.get("result", {}).get("records", []))
        if not records and "data" in data:
            records = data["data"].get("records", [])

        papers = [self._parse_record(r) for r in records]

        if filters.year_from:
            papers = [p for p in papers if p.year is None or p.year >= filters.year_from]
        if filters.year_to:
            papers = [p for p in papers if p.year is None or p.year <= filters.year_to]

        return papers

    async def get_by_id(self, paper_id: str) -> Paper | None:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{self.RECORD_URL}/{paper_id}")
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            data = resp.json()
            record = data.get("data", data)
            return self._parse_record(record)
