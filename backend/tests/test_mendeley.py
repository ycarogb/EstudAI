from app.analysis.collection import find_shared_references
from app.importers.mendeley import match_pdf_to_paper, parse_mendeley_export
from app.models.schemas import Paper, PaperSource


def test_parse_mendeley_bibtex():
    bib = """
@article{smith2023,
  title = {Machine Learning in Education},
  author = {Smith, John},
  year = {2023},
  abstract = {This study explores ML in higher education.}
}
"""
    papers = parse_mendeley_export("mendeley.bib", bib)
    assert len(papers) == 1
    assert papers[0].source == PaperSource.MENDELEY
    assert papers[0].title == "Machine Learning in Education"


def test_find_shared_references():
    papers = [
        Paper(
            id="1",
            source=PaperSource.MENDELEY,
            title="Paper A",
            cited_references=["Vygotsky, 1978. Mind in Society", "Piaget, 1950"],
        ),
        Paper(
            id="2",
            source=PaperSource.MENDELEY,
            title="Paper B",
            cited_references=["Vygotsky, 1978. Mind in Society", "Freire, 1970"],
        ),
    ]
    shared = find_shared_references(papers)
    assert len(shared) >= 1
    assert shared[0].count == 2


def test_match_pdf_to_paper():
    papers = [
        Paper(
            id="1",
            source=PaperSource.MENDELEY,
            title="Machine Learning in Education",
            authors=["Smith, John"],
        )
    ]
    match = match_pdf_to_paper("Smith_Machine_Learning_in_Education.pdf", papers)
    assert match is not None
    assert match.id == "1"
