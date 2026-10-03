from app.enrichment.paper_enricher import (
    determine_text_source,
    has_analyzable_text,
    text_source_label,
)
from app.models.schemas import Paper, PaperSource


def test_has_analyzable_text_with_abstract():
    paper = Paper(id="1", source=PaperSource.MENDELEY, title="T", abstract="x" * 150)
    assert has_analyzable_text(paper)


def test_has_analyzable_text_metadata_only():
    paper = Paper(id="1", source=PaperSource.MENDELEY, title="T", authors=["A"], year=2020)
    assert not has_analyzable_text(paper)


def test_text_source_label_pdf_local():
    paper = Paper(
        id="1",
        source=PaperSource.MENDELEY,
        title="T",
        abstract="x" * 150,
        pdf_url="local://foo.pdf",
    )
    paper.text_source = determine_text_source(paper)
    assert text_source_label(paper) == "Texto completo (PDF local)"
