import pytest
from app.models.schemas import Paper, PaperSource, SearchFilters
from app.search.base import make_paper_id, normalize_title
from app.search.hub import SearchHub
from app.importers.ris_bibtex import parse_bibtex, papers_to_csv


def test_normalize_title():
    assert normalize_title("Hello World!") == "hello world"
    assert normalize_title("Título com Acentos") == "titulo com acentos"


def test_make_paper_id():
    id1 = make_paper_id("openalex", "W123")
    id2 = make_paper_id("openalex", "W123")
    id3 = make_paper_id("openalex", "W456")
    assert id1 == id2
    assert id1 != id3


def test_deduplicate_by_doi():
    hub = SearchHub()
    papers = [
        Paper(id="1", source=PaperSource.OPENALEX, title="Paper A", doi="10.1234/test", authors=[]),
        Paper(id="2", source=PaperSource.SEMANTIC_SCHOLAR, title="Paper A copy", doi="10.1234/test", authors=[], abstract="More detail"),
    ]
    result = hub._deduplicate(papers)
    assert len(result) == 1
    assert result[0].abstract == "More detail"


def test_parse_bibtex():
    bib = """
@article{test2024,
  title = {Test Paper},
  author = {Silva, João and Santos, Maria},
  year = {2024},
  doi = {10.1234/test}
}
"""
    papers = parse_bibtex(bib)
    assert len(papers) == 1
    assert papers[0].title == "Test Paper"
    assert papers[0].year == 2024
    assert len(papers[0].authors) == 2


def test_papers_to_csv():
    papers = [
        Paper(
            id="1",
            source=PaperSource.OPENALEX,
            title="Test",
            authors=["Author"],
            year=2024,
            objectives="Objetivo teste",
        )
    ]
    csv_out = papers_to_csv(papers)
    assert "Test" in csv_out
    assert "Objetivo teste" in csv_out
