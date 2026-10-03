import asyncio
import logging

from app.models.schemas import Paper, PaperSource, SearchFilters
from app.search.base import SearchAdapter, normalize_title
from app.search.bdtd import BDTDAdapter
from app.search.openalex import OpenAlexAdapter
from app.search.scopus import ScopusAdapter
from app.search.wos import WOSAdapter
from app.search.semantic_scholar import SemanticScholarAdapter

logger = logging.getLogger(__name__)

DEFAULT_SOURCES = [
    PaperSource.OPENALEX,
    PaperSource.SEMANTIC_SCHOLAR,
    PaperSource.BDTD,
]


class SearchHub:
    def __init__(self) -> None:
        self._adapters: dict[PaperSource, SearchAdapter] = {
            PaperSource.OPENALEX: OpenAlexAdapter(),
            PaperSource.SEMANTIC_SCHOLAR: SemanticScholarAdapter(),
            PaperSource.BDTD: BDTDAdapter(),
            PaperSource.SCOPUS: ScopusAdapter(),
            PaperSource.WOS: WOSAdapter(),
        }

    def _resolve_sources(self, filters: SearchFilters) -> list[PaperSource]:
        if filters.sources:
            return filters.sources
        return DEFAULT_SOURCES

    async def search(self, query: str, filters: SearchFilters | None = None) -> list[Paper]:
        filters = filters or SearchFilters()
        sources = self._resolve_sources(filters)

        tasks = []
        for source in sources:
            adapter = self._adapters.get(source)
            if adapter:
                tasks.append(self._safe_search(adapter, query, filters))

        results = await asyncio.gather(*tasks)
        all_papers: list[Paper] = []
        for batch in results:
            all_papers.extend(batch)

        deduped = self._deduplicate(all_papers)
        ranked = self._rank(deduped, query)
        return ranked[: filters.limit]

    async def _safe_search(
        self, adapter: SearchAdapter, query: str, filters: SearchFilters
    ) -> list[Paper]:
        try:
            return await adapter.search(query, filters)
        except Exception as e:
            logger.warning("Search failed for %s: %s", adapter.name, e)
            return []

    def _deduplicate(self, papers: list[Paper]) -> list[Paper]:
        seen_doi: dict[str, Paper] = {}
        seen_title: dict[str, Paper] = {}
        result: list[Paper] = []

        for paper in papers:
            if paper.doi:
                doi_key = paper.doi.lower().strip()
                if doi_key in seen_doi:
                    self._merge_paper(seen_doi[doi_key], paper)
                    continue
                seen_doi[doi_key] = paper
                result.append(paper)
                continue

            title_key = normalize_title(paper.title)
            if title_key in seen_title:
                self._merge_paper(seen_title[title_key], paper)
                continue
            seen_title[title_key] = paper
            result.append(paper)

        return result

    def _merge_paper(self, existing: Paper, new: Paper) -> None:
        if not existing.abstract and new.abstract:
            existing.abstract = new.abstract
        if not existing.doi and new.doi:
            existing.doi = new.doi
        if not existing.pdf_url and new.pdf_url:
            existing.pdf_url = new.pdf_url
        if not existing.url and new.url:
            existing.url = new.url

    def _rank(self, papers: list[Paper], query: str) -> list[Paper]:
        query_terms = set(normalize_title(query).split())

        def score(paper: Paper) -> float:
            s = 0.0
            title_terms = set(normalize_title(paper.title).split())
            overlap = len(query_terms & title_terms)
            s += overlap * 2.0

            if paper.abstract:
                abstract_terms = set(normalize_title(paper.abstract[:500]).split())
                s += len(query_terms & abstract_terms) * 0.5

            if paper.year:
                from datetime import datetime

                age = datetime.now().year - paper.year
                s += max(0, 5 - age * 0.3)

            if paper.source == PaperSource.BDTD:
                s += 0.5

            paper.relevance_score = round(s, 2)
            return s

        papers.sort(key=score, reverse=True)
        return papers


search_hub = SearchHub()
