import csv
import io
import re

import bibtexparser
import rispy

from app.models.schemas import Paper, PaperSource
from app.search.base import make_paper_id


def parse_ris(content: str) -> list[Paper]:
    entries = rispy.loads(content)
    papers = []
    for entry in entries:
        title = entry.get("title") or entry.get("primary_title") or "Sem título"
        authors = entry.get("authors", [])
        year = entry.get("year") or entry.get("publication_year")
        if isinstance(year, str):
            try:
                year = int(year[:4])
            except ValueError:
                year = None

        doi = entry.get("doi")
        abstract = entry.get("abstract")
        url = entry.get("url") or entry.get("link")

        paper_id = make_paper_id("import", doi or title)
        papers.append(
            Paper(
                id=paper_id,
                source=PaperSource.IMPORT,
                title=title,
                authors=authors if isinstance(authors, list) else [authors],
                year=year,
                abstract=abstract,
                doi=doi,
                url=url,
                pdf_url=None,
                keywords=entry.get("keywords", []),
                document_type=entry.get("type_of_reference"),
            )
        )
    return papers


def parse_bibtex(content: str) -> list[Paper]:
    bib_db = bibtexparser.loads(content)
    papers = []
    for entry in bib_db.entries:
        title = entry.get("title", "Sem título").strip("{}")
        authors_raw = entry.get("author", "")
        authors = [a.strip() for a in re.split(r"\s+and\s+", authors_raw)] if authors_raw else []

        year = entry.get("year")
        if year:
            try:
                year = int(str(year)[:4])
            except ValueError:
                year = None

        doi = entry.get("doi", "").strip("{}")
        abstract = entry.get("abstract", "").strip("{}")
        url = entry.get("url", "").strip("{}")

        paper_id = make_paper_id("import", doi or entry.get("ID", title))
        papers.append(
            Paper(
                id=paper_id,
                source=PaperSource.IMPORT,
                title=title,
                authors=authors,
                year=year,
                abstract=abstract or None,
                doi=doi or None,
                url=url or None,
                pdf_url=None,
                keywords=[],
                document_type=entry.get("ENTRYTYPE"),
            )
        )
    return papers


def parse_csv_references(content: str) -> list[Paper]:
    reader = csv.DictReader(io.StringIO(content))
    papers = []
    for row in reader:
        title = row.get("title") or row.get("Title") or row.get("Título") or "Sem título"
        authors_raw = row.get("authors") or row.get("Authors") or row.get("Autores") or ""
        authors = [a.strip() for a in authors_raw.split(";") if a.strip()] if authors_raw else []

        year_val = row.get("year") or row.get("Year") or row.get("Ano")
        year = None
        if year_val:
            try:
                year = int(str(year_val)[:4])
            except ValueError:
                pass

        paper_id = make_paper_id("import", row.get("doi", title))
        papers.append(
            Paper(
                id=paper_id,
                source=PaperSource.IMPORT,
                title=title,
                authors=authors,
                year=year,
                abstract=row.get("abstract") or row.get("Abstract"),
                doi=row.get("doi"),
                url=row.get("url"),
                pdf_url=None,
                keywords=[],
                document_type=row.get("type"),
            )
        )
    return papers


def parse_import_file(filename: str, content: str) -> list[Paper]:
    lower = filename.lower()
    if lower.endswith(".ris"):
        return parse_ris(content)
    if lower.endswith(".bib") or lower.endswith(".bibtex"):
        return parse_bibtex(content)
    if lower.endswith(".csv"):
        return parse_csv_references(content)
    if content.strip().startswith("@"):
        return parse_bibtex(content)
    return parse_ris(content)


def papers_to_bibtex(papers: list[Paper]) -> str:
    entries = []
    for i, p in enumerate(papers):
        key = re.sub(r"[^\w]", "", p.title[:20].lower()) or f"ref{i}"
        authors = " and ".join(p.authors) if p.authors else "Unknown"
        lines = [f"@article{{{key},"]
        lines.append(f"  title = {{{p.title}}},")
        lines.append(f"  author = {{{authors}}},")
        if p.year:
            lines.append(f"  year = {{{p.year}}},")
        if p.doi:
            lines.append(f"  doi = {{{p.doi}}},")
        if p.url:
            lines.append(f"  url = {{{p.url}}},")
        if p.abstract:
            lines.append(f"  abstract = {{{p.abstract[:500]}}},")
        lines.append("}")
        entries.append("\n".join(lines))
    return "\n\n".join(entries)


def papers_to_csv(papers: list[Paper]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "title", "authors", "year", "source", "doi", "url",
        "objectives", "results", "gaps", "methods", "scope", "geographic_scope", "abstract",
    ])
    for p in papers:
        writer.writerow([
            p.title,
            "; ".join(p.authors),
            p.year or "",
            p.source.value,
            p.doi or "",
            p.url or "",
            p.objectives or "",
            p.results or "",
            p.gaps or "",
            p.methods or "",
            p.scope or "",
            p.geographic_scope or "",
            (p.abstract or "")[:500],
        ])
    return output.getvalue()
