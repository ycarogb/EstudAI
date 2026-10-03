"""Chat contextual sobre análise de PDFs já realizada."""

from app.agents.prompts import PDF_ANALYSIS_CHAT_SYSTEM
from app.extraction.llm import call_llm
from app.models.schemas import CorrelationInsight, PDFPaperResult, PdfAnalysisChatMessage


def _build_analysis_context(
    papers: list[PDFPaperResult],
    correlations: list[CorrelationInsight],
    narrative: str,
) -> str:
    parts: list[str] = []

    if narrative:
        parts.append(f"## Síntese da coleção\n{narrative[:2000]}")

    parts.append(f"## Trabalhos analisados ({len(papers)})\n")
    for i, p in enumerate(papers[:40], 1):
        if p.error:
            parts.append(f"### {i}. {p.title} — ERRO: {p.error}")
            continue
        block = [f"### {i}. {p.title}"]
        if p.authors:
            block.append(f"Autores: {', '.join(p.authors[:4])}")
        if p.year:
            block.append(f"Ano: {p.year}")
        if p.objectives:
            block.append(f"Objetivos: {p.objectives[:500]}")
        if p.methodology:
            block.append(f"Metodologia: {p.methodology[:400]}")
        if p.results:
            block.append(f"Resultados: {p.results[:500]}")
        if p.gaps:
            block.append(f"Lacunas: {p.gaps[:400]}")
        parts.append("\n".join(block))

    if correlations:
        parts.append("\n## Correlações identificadas\n")
        for c in correlations[:20]:
            papers_ref = ", ".join(c.papers[:4]) if c.papers else "—"
            parts.append(
                f"- **{c.title}** ({c.category}): {c.description[:400]}\n"
                f"  Trabalhos: {papers_ref}"
            )

    return "\n\n".join(parts)[:28000]


async def chat_about_pdf_analysis(
    message: str,
    papers: list[PDFPaperResult],
    correlations: list[CorrelationInsight],
    narrative: str,
    history: list[PdfAnalysisChatMessage],
) -> str:
    context = _build_analysis_context(papers, correlations, narrative)

    history_text = ""
    if history:
        lines = []
        for msg in history[-8:]:
            role = "Usuário" if msg.role == "user" else "Assistente"
            lines.append(f"{role}: {msg.content[:800]}")
        history_text = "\n\nHistórico recente da conversa:\n" + "\n".join(lines)

    user_prompt = f"""Dados da análise de PDFs:

{context}
{history_text}

Pergunta do usuário: {message}

Instruções para esta resposta:
- Responda diretamente à pergunta acima, sem ser genérico.
- Use apenas evidências presentes nos dados.
- Termine obrigatoriamente com o bloco **Em resumo:** (1 a 3 frases objetivas)."""

    return await call_llm(PDF_ANALYSIS_CHAT_SYSTEM, user_prompt)
