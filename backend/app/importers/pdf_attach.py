import fitz

from app.importers.mendeley import match_pdf_to_paper
from app.models.schemas import Paper


def extract_text_from_pdf_bytes(content: bytes, max_length: int = 12000) -> str:
    doc = fitz.open(stream=content, filetype="pdf")
    parts = []
    for page in doc:
        parts.append(page.get_text())
    doc.close()
    return "\n".join(parts)[:max_length]


async def attach_pdfs_to_papers(
    papers: list[Paper],
    files: list[tuple[str, bytes]],
) -> tuple[list[Paper], list[str]]:
    """Associa PDFs aos trabalhos e retorna lista de arquivos não correspondidos."""
    paper_map = {p.id: p for p in papers}
    unmatched: list[str] = []

    for filename, content in files:
        match = match_pdf_to_paper(filename, papers)
        if not match:
            unmatched.append(filename)
            continue
        text = extract_text_from_pdf_bytes(content)
        if text.strip():
            paper = paper_map[match.id]
            paper.pdf_url = f"local://{filename}"
            paper.abstract = text[:12000]

    return list(paper_map.values()), unmatched
