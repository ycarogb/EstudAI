"""
Enriquecimento de papers importados do Mendeley (ou outras fontes de metadados).

Pipeline por paper:
  1. DOI disponível  → OpenAlex → Semantic Scholar → Crossref (abstract)
  2. Sem DOI         → Crossref por título (obtém DOI + abstract)
                     → OpenAlex por título
                     → Semantic Scholar por título
  3. Determina text_source e registra no Paper

Execução paralela com semáforo para não sobrecarregar as APIs.
"""

import asyncio
import logging
import re
from difflib import SequenceMatcher

import httpx

from app.config import settings
from app.models.schemas import Paper, TextSource
from app.search.openalex import OpenAlexAdapter
from app.search.semantic_scholar import SemanticScholarAdapter

logger = logging.getLogger(__name__)

MIN_ABSTRACT_LEN = 120
_ENRICH_CONCURRENCY = 5  # requisições paralelas máximas


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).strip()


def _title_similarity(a: str, b: str) -> float:
    from app.search.base import normalize_title
    return SequenceMatcher(None, normalize_title(a)[:120], normalize_title(b)[:120]).ratio()


def has_analyzable_text(paper: Paper) -> bool:
    if paper.pdf_url and not paper.pdf_url.startswith("local://"):
        return True
    if paper.pdf_url and paper.pdf_url.startswith("local://"):
        return bool(paper.abstract and len(paper.abstract.strip()) >= MIN_ABSTRACT_LEN)
    return bool(paper.abstract and len(paper.abstract.strip()) >= MIN_ABSTRACT_LEN)


def determine_text_source(paper: Paper) -> str:
    if paper.pdf_url:
        if paper.pdf_url.startswith("local://"):
            return TextSource.PDF_LOCAL
        return TextSource.PDF_OPEN
    if paper.abstract and len(paper.abstract.strip()) >= MIN_ABSTRACT_LEN:
        # If this abstract came from Crossref, the caller will override to crossref_abstract
        return TextSource.ABSTRACT
    return TextSource.METADATA_ONLY


def text_source_label(paper: Paper) -> str:
    from app.models.schemas import TEXT_SOURCE_LABELS
    return TEXT_SOURCE_LABELS.get(paper.text_source or "", "Desconhecido")


# ---------------------------------------------------------------------------
# Crossref
# ---------------------------------------------------------------------------

async def _crossref_by_doi(doi: str) -> dict | None:
    clean = doi.replace("https://doi.org/", "").strip()
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"https://api.crossref.org/works/{clean}",
                params={"select": "DOI,title,abstract,author,published-print,published-online,issued"},
                headers={"User-Agent": "EstudAI/1.0 (mailto:estudai@research.br)"},
            )
            if resp.status_code != 200:
                return None
            return resp.json().get("message")
    except Exception as e:
        logger.debug("Crossref DOI lookup failed for %s: %s", doi, e)
        return None


async def _crossref_by_title(title: str) -> dict | None:
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://api.crossref.org/works",
                params={
                    "query.bibliographic": title[:200],
                    "rows": 3,
                    "select": "DOI,title,abstract,author,published-print,published-online,issued,score",
                },
                headers={"User-Agent": "EstudAI/1.0 (mailto:estudai@research.br)"},
            )
            if resp.status_code != 200:
                return None
            items = resp.json().get("message", {}).get("items", [])
            # pick the item whose title best matches
            for item in items:
                cr_titles = item.get("title", [])
                if not cr_titles:
                    continue
                sim = _title_similarity(title, cr_titles[0])
                if sim >= 0.55:
                    return item
            return None
    except Exception as e:
        logger.debug("Crossref title search failed for '%s': %s", title[:50], e)
        return None


def _parse_crossref(work: dict) -> dict:
    """Extract usable fields from a Crossref work object."""
    doi = work.get("DOI", "") or ""

    abstract = _strip_html(work.get("abstract", "") or "")

    year = None
    for date_field in ("published-print", "published-online", "issued"):
        parts = work.get(date_field, {}).get("date-parts", [[]])
        if parts and parts[0]:
            try:
                year = int(parts[0][0])
                break
            except (ValueError, TypeError):
                pass

    authors = []
    for a in work.get("author", []):
        family = a.get("family", "")
        given = a.get("given", "")
        if family:
            authors.append(f"{family}, {given}".strip(", "))

    titles = work.get("title", [])
    title = titles[0] if titles else ""

    return {
        "doi": doi,
        "title": title,
        "abstract": abstract or None,
        "year": year,
        "authors": authors,
    }


# ---------------------------------------------------------------------------
# OpenAlex
# ---------------------------------------------------------------------------

async def _openalex_by_doi(doi: str) -> Paper | None:
    adapter = OpenAlexAdapter()
    clean = doi.replace("https://doi.org/", "").strip()
    try:
        params: dict = {}
        if settings.openalex_email:
            params["mailto"] = settings.openalex_email
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(
                f"https://api.openalex.org/works/https://doi.org/{clean}",
                params=params,
            )
            if resp.status_code != 200:
                return None
            return adapter._parse_work(resp.json())
    except Exception as e:
        logger.debug("OpenAlex DOI lookup failed for %s: %s", doi, e)
        return None


async def _openalex_by_title(title: str) -> Paper | None:
    adapter = OpenAlexAdapter()
    from app.models.schemas import SearchFilters
    try:
        results = await adapter.search(title[:200], SearchFilters(limit=1))
        if not results:
            return None
        # accept only if title similarity is high
        if _title_similarity(title, results[0].title) >= 0.50:
            return results[0]
        return None
    except Exception as e:
        logger.debug("OpenAlex title search failed for '%s': %s", title[:50], e)
        return None


# ---------------------------------------------------------------------------
# Semantic Scholar
# ---------------------------------------------------------------------------

async def _s2_by_doi(doi: str) -> Paper | None:
    adapter = SemanticScholarAdapter()
    clean = doi.replace("https://doi.org/", "").strip()
    try:
        fields = "paperId,title,abstract,year,authors,externalIds,openAccessPdf"
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(
                f"https://api.semanticscholar.org/graph/v1/paper/DOI:{clean}",
                params={"fields": fields},
                headers=adapter._headers(),
            )
            if resp.status_code != 200:
                return None
            return adapter._parse_paper(resp.json())
    except Exception as e:
        logger.debug("S2 DOI lookup failed for %s: %s", doi, e)
        return None


async def _s2_by_title(title: str) -> Paper | None:
    adapter = SemanticScholarAdapter()
    from app.models.schemas import SearchFilters
    try:
        results = await adapter.search(title[:200], SearchFilters(limit=1))
        if not results:
            return None
        if _title_similarity(title, results[0].title) >= 0.50:
            return results[0]
        return None
    except Exception as e:
        logger.debug("S2 title search failed for '%s': %s", title[:50], e)
        return None


# ---------------------------------------------------------------------------
# Merge helpers
# ---------------------------------------------------------------------------

def _merge(target: Paper, source: Paper) -> None:
    """Copy missing fields from source into target (in-place)."""
    if not target.abstract and source.abstract:
        target.abstract = source.abstract
    if not target.pdf_url and source.pdf_url:
        target.pdf_url = source.pdf_url
    if not target.doi and source.doi:
        target.doi = source.doi
    if not target.url and source.url:
        target.url = source.url
    if not target.year and source.year:
        target.year = source.year
    if not target.authors and source.authors:
        target.authors = source.authors


def _merge_crossref(target: Paper, cr: dict) -> None:
    if not target.abstract and cr.get("abstract"):
        target.abstract = cr["abstract"]
    if not target.doi and cr.get("doi"):
        target.doi = cr["doi"]
    if not target.year and cr.get("year"):
        target.year = cr["year"]
    if not target.authors and cr.get("authors"):
        target.authors = cr["authors"]


# ---------------------------------------------------------------------------
# Core enrichment
# ---------------------------------------------------------------------------

async def enrich_paper(paper: Paper) -> Paper:
    """
    Enriquece um Paper com abstract/PDF aberto, tentando múltiplas fontes.
    Define paper.text_source com o resultado alcançado.
    """
    # Fast path: já tem texto suficiente
    if has_analyzable_text(paper):
        if not paper.text_source:
            paper.text_source = determine_text_source(paper)
        return paper

    crossref_abstract = False

    # ---- Caminho 1: tem DOI ----
    if paper.doi:
        # 1a. OpenAlex por DOI
        oa = await _openalex_by_doi(paper.doi)
        if oa:
            _merge(paper, oa)

        # 1b. Semantic Scholar por DOI (pega openAccessPdf)
        if not has_analyzable_text(paper):
            s2 = await _s2_by_doi(paper.doi)
            if s2:
                _merge(paper, s2)

        # 1c. Crossref por DOI (abstract em alguns publishers)
        if not has_analyzable_text(paper):
            cr_work = await _crossref_by_doi(paper.doi)
            if cr_work:
                cr = _parse_crossref(cr_work)
                _merge_crossref(paper, cr)
                if cr.get("abstract"):
                    crossref_abstract = True

    # ---- Caminho 2: sem DOI (ou DOI não ajudou) ----
    if not has_analyzable_text(paper) and paper.title:
        # 2a. Crossref por título → recupera DOI + abstract
        cr_work = await _crossref_by_title(paper.title)
        if cr_work:
            cr = _parse_crossref(cr_work)
            _merge_crossref(paper, cr)
            if cr.get("abstract"):
                crossref_abstract = True
            # Se agora temos DOI, tentar OpenAlex para PDF aberto
            if paper.doi and not paper.pdf_url:
                oa = await _openalex_by_doi(paper.doi)
                if oa:
                    _merge(paper, oa)

    if not has_analyzable_text(paper) and paper.title:
        # 2b. OpenAlex por título
        oa = await _openalex_by_title(paper.title)
        if oa:
            _merge(paper, oa)

    if not has_analyzable_text(paper) and paper.title:
        # 2c. Semantic Scholar por título
        s2 = await _s2_by_title(paper.title)
        if s2:
            _merge(paper, s2)

    # ---- Definir text_source ----
    source = determine_text_source(paper)
    # override se abstract veio do Crossref e não há PDF
    if (
        crossref_abstract
        and source == TextSource.ABSTRACT
        and not paper.pdf_url
    ):
        source = TextSource.CROSSREF_ABSTRACT

    paper.text_source = source
    return paper


async def enrich_papers(papers: list[Paper]) -> tuple[list[Paper], dict]:
    """Enriquece papers em paralelo (até _ENRICH_CONCURRENCY simultâneos)."""
    sem = asyncio.Semaphore(_ENRICH_CONCURRENCY)

    async def _bounded(p: Paper) -> Paper:
        async with sem:
            return await enrich_paper(p)

    results = await asyncio.gather(*[_bounded(p) for p in papers])
    results = list(results)

    from collections import Counter
    breakdown: dict[str, int] = Counter(
        p.text_source or TextSource.METADATA_ONLY for p in results
    )

    with_text = sum(1 for p in results if has_analyzable_text(p))
    without_text = len(results) - with_text

    return results, {
        "total": len(results),
        "with_text": with_text,
        "without_text": without_text,
        "coverage_percent": round(100 * with_text / len(results)) if results else 0,
        "text_source_breakdown": dict(breakdown),
    }
