import re

from app.importers.ris_bibtex import parse_import_file
from app.models.schemas import Paper, PaperSource
from app.search.base import make_paper_id, normalize_title


def _split_keywords(raw: str | list | None) -> list[str]:
    if not raw:
        return []
    if isinstance(raw, list):
        return [str(k).strip() for k in raw if k]
    return [k.strip() for k in re.split(r"[;,]", str(raw)) if k.strip()]


def parse_mendeley_export(filename: str, content: str) -> list[Paper]:
    """Importa exportação BibTeX/RIS do Mendeley."""
    papers = parse_import_file(filename, content)
    for paper in papers:
        paper.source = PaperSource.MENDELEY
        paper.id = make_paper_id("mendeley", paper.doi or paper.title)
    return papers


def match_pdf_to_paper(filename: str, papers: list[Paper]) -> Paper | None:
    """Associa PDF ao trabalho pelo nome do arquivo."""
    stem = re.sub(r"\.pdf$", "", filename, flags=re.I)
    stem = re.sub(r"[_\-.]+", " ", stem)
    stem_key = normalize_title(stem)
    if not stem_key:
        return None

    best: Paper | None = None
    best_score = 0.0

    for paper in papers:
        title_key = normalize_title(paper.title)
        if not title_key:
            continue

        if stem_key == title_key or stem_key in title_key or title_key in stem_key:
            score = len(stem_key) / max(len(title_key), 1)
            if score > best_score:
                best_score = score
                best = paper

        if paper.authors:
            author_part = normalize_title(paper.authors[0].split(",")[0])
            if author_part and author_part in stem_key and title_key[:20] in stem_key:
                if 0.5 > best_score:
                    best = paper
                    best_score = 0.5

    return best
