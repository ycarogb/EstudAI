"""
Processamento em lote de PDFs: extração individual por LLM e análise de
correlações cruzadas entre os trabalhos da coleção.
"""

import logging
import re

from app.extraction.llm import call_llm, parse_extraction_response
from app.models.schemas import CitationSpan, CorrelationInsight, PDFPaperResult

logger = logging.getLogger(__name__)

MAX_TEXT_CHARS = 28_000
_HEAD_CHARS = 5_000
_TAIL_CHARS = 5_000
_GAP_BUDGET = 14_000
_SECTION_WINDOW_AFTER = 12_000

# Padrões de alta prioridade (seções explícitas de lacunas/limitações)
_HIGH_PRIORITY_GAP_PATTERNS = [
    r"limita[cç][oõ]es\s+e\s+sugest[oõ]es",
    r"limita[cç][oõ]es\s+do\s+estudo",
    r"limita[cç][oõ]es\s+da\s+pesquisa",
    r"limita[cç][oõ]es",
    r"sugest[oõ]es\s+para\s+pesquisas?\s+futuras?",
    r"sugest[oõ]es\s+para\s+trabalhos?\s+futuros?",
    r"lacunas?\s+identificadas?",
    r"lacunas?\s+da\s+pesquisa",
    r"lacunas?\s+do\s+estudo",
    r"limitations?\s+and\s+suggestions?",
    r"limitations?\s+of\s+the\s+(study|research)",
    r"limitations?",
    r"future\s+(work|research|studies)",
]

# Padrões secundários (quando não há seção explícita)
_SECONDARY_GAP_PATTERNS = [
    r"pesquisas?\s+futuras?",
    r"trabalhos?\s+futuros?",
    r"recomenda[cç][oõ]es\s+para\s+pesquisas?",
    r"perspectivas?\s+de\s+pesquisa",
    r"considera[cç][oõ]es\s+finais",
    r"conclus[oõ]es?\s+e\s+sugest[oõ]es",
    r"conclus[oõ]es?\s+finais",
    r"discuss[aã]o",
    r"s[ií]ntese\s+final",
]

_GAP_SECTION_PATTERNS = _HIGH_PRIORITY_GAP_PATTERNS + _SECONDARY_GAP_PATTERNS

PDF_EXTRACTION_SYSTEM = """Você é especialista em revisão bibliográfica e análise crítica de produção acadêmica.
O PDF pode ser artigo científico, dissertação de mestrado, tese de doutorado, capítulo ou relatório técnico.
Adapte a leitura à estrutura do documento (artigos são mais curtos; dissertações/teses têm capítulos e seções finais extensas).

Responda APENAS com JSON válido no formato:
{
  "document_type": "artigo|dissertacao|tese|outro",
  "title": "título completo do trabalho",
  "authors": ["Sobrenome, Nome"],
  "year": 2024,
  "objectives": "objetivos principais em 2-4 frases",
  "methodology": "métodos, técnicas e abordagem metodológica",
  "results": "principais resultados e conclusões em 2-4 frases",
  "gaps": "TODAS as lacunas, limitações e sugestões de pesquisa futura declaradas pelos autores",
  "citations": [
    {"field": "objectives|methodology|results|gaps", "text": "resumo da extração", "source_text": "trecho literal do PDF"}
  ]
}

Regras gerais:
- Extraia title e authors do cabeçalho, folha de rosto ou primeiras páginas.
- Responda em português, mesmo que o PDF esteja em inglês.
- Se alguma informação não estiver disponível, use null para strings ou [] para listas.

Campo gaps — PRIORIDADE MÁXIMA:
- Busque ativamente seções como: Limitações e Sugestões, Limitações, Sugestões para Pesquisas Futuras,
  Lacunas, Considerações Finais, Conclusões, Discussão, Perspectivas, Recomendações, Future Work, Limitations.
- Em dissertações e teses, as lacunas costumam estar no capítulo final ou em subseções de Conclusão/Considerações Finais.
- Inclua: (1) limitações metodológicas declaradas pelos autores; (2) limitações de escopo/amostra/contexto;
  (3) lacunas no conhecimento que os autores reconhecem; (4) sugestões explícitas de estudos futuros.
- NÃO invente lacunas. NÃO confunda resultados com lacunas. NÃO use frases genéricas.
- Se houver seção de limitações/sugestões no texto fornecido, transcreva e sintetize fielmente cada ponto.
- Se o título da seção aparecer acompanhado de parágrafos logo abaixo, extraia esse conteúdo — não diga que o texto está ausente se houver parágrafos após o título.
- Formate gaps como lista numerada ou tópicos separados por ponto e vírgula quando houver múltiplos itens.
- Use null em gaps somente se realmente não houver nenhuma limitação, lacuna ou sugestão no material fornecido.

Citações (citations):
- Inclua pelo menos 1 citação com field=gaps quando houver limitações/lacunas no texto.
- source_text deve ser trecho literal do PDF (não parafraseie na citação)."""

CORRELATION_SYSTEM = """Você é especialista em síntese de literatura científica para revisão sistemática de tese.
Analise os dados extraídos de múltiplos trabalhos e identifique padrões e correlações.
Responda APENAS com JSON no formato:
{
  "correlations": [
    {
      "category": "conclusoes_comuns|lacunas_comuns|padroes_metodologicos|divergencias|tendencias|insights",
      "title": "Título conciso do insight",
      "description": "Descrição direta em 2-4 frases: o padrão, quais trabalhos compartilham e a implicação para a pesquisa",
      "papers": ["Título do trabalho 1", "Título do trabalho 2"]
    }
  ],
  "narrative": "Síntese objetiva em 3-4 frases: o que a coleção revela sobre o estado da arte e qual a principal oportunidade de pesquisa identificada"
}
Gere pelo menos um insight por categoria disponível. Seja específico aos trabalhos analisados — evite generalidades."""


def _extract_pdf_pages(content: bytes) -> list[str]:
    try:
        import fitz

        doc = fitz.open(stream=content, filetype="pdf")
        pages = [page.get_text() for page in doc]
        doc.close()
        return pages
    except Exception as exc:
        logger.warning("PyMuPDF extraction failed: %s", exc)
        return []


def _extract_pdf_text(content: bytes) -> str:
    return "\n".join(_extract_pdf_pages(content))


def _is_toc_line(line: str) -> bool:
    """Detecta linha de sumário (título + pontinhos + número de página)."""
    stripped = line.strip()
    if not stripped or len(stripped) > 180:
        return False
    if re.search(r"\.{4,}", stripped):
        return True
    if re.search(r"\.{2,}\s*\d+\s*$", stripped):
        return True
    if re.match(r"^[\d\.\s]+$", stripped):
        return True
    return False


def _score_section_match(full_text: str, match: re.Match, pattern_priority: float) -> float:
    """Pontua ocorrências: prefere corpo do texto (não sumário) e conteúdo após o título."""
    pos = match.start()
    doc_len = max(len(full_text), 1)
    rel_pos = pos / doc_len

    line_start = full_text.rfind("\n", 0, pos) + 1
    line_end = full_text.find("\n", pos)
    line = full_text[line_start:line_end if line_end != -1 else pos + 200]

    after = full_text[match.end() : match.end() + 2500]
    prose_after = len(re.sub(r"\s+", " ", after.strip()))

    score = pattern_priority
    if rel_pos >= 0.45:
        score += 3.0
    elif rel_pos >= 0.25:
        score += 1.0
    else:
        score -= 2.0

    if prose_after >= 350:
        score += 5.0
    elif prose_after >= 120:
        score += 2.5
    elif prose_after < 60:
        score -= 3.0

    if _is_toc_line(line):
        score -= 8.0

    return score


def _score_page_match(page: str, match: re.Match, page_idx: int, total_pages: int, pattern_priority: float) -> float:
    """Pontua match em uma página — útil quando o título está no fim da página anterior."""
    rel_page = page_idx / max(total_pages - 1, 1)
    line_start = page.rfind("\n", 0, match.start()) + 1
    line_end = page.find("\n", match.start())
    line = page[line_start:line_end if line_end != -1 else match.start() + 200]
    after = page[match.end() :]
    prose_after = len(re.sub(r"\s+", " ", after.strip()))

    score = pattern_priority + rel_page * 4.0
    if prose_after >= 200:
        score += 5.0
    elif prose_after >= 60:
        score += 2.0
    elif page_idx < total_pages - 1:
        # Título no fim da página: conteúdo pode estar nas próximas
        score += 1.5

    if _is_toc_line(line):
        score -= 8.0

    return score


def _extract_gap_text_from_pages(pages: list[str]) -> str:
    """Extrai páginas da seção real de limitações (evita sumário)."""
    if not pages:
        return ""

    pattern_groups = [
        (6.0, _HIGH_PRIORITY_GAP_PATTERNS),
        (2.0, _SECONDARY_GAP_PATTERNS),
    ]

    best_page = -1
    best_score = -999.0

    for priority, patterns in pattern_groups:
        for page_idx, page in enumerate(pages):
            for pattern in patterns:
                for match in re.finditer(pattern, page, re.IGNORECASE):
                    score = _score_page_match(page, match, page_idx, len(pages), priority)
                    if score > best_score:
                        best_score = score
                        best_page = page_idx

    if best_page < 0 or best_score < 0:
        return ""

    # Inclui a página do match e até 4 páginas seguintes (conteúdo da seção)
    end_page = min(len(pages), best_page + 5)
    return "\n\n".join(p.strip() for p in pages[best_page:end_page] if p.strip())


def _extract_gap_sections(full_text: str) -> list[str]:
    """Localiza trechos com seções de limitações no texto contínuo (fallback)."""
    if not full_text.strip():
        return []

    lower = full_text.lower()
    candidates: list[tuple[float, int, int]] = []

    pattern_groups = [
        (6.0, _HIGH_PRIORITY_GAP_PATTERNS),
        (2.0, _SECONDARY_GAP_PATTERNS),
    ]

    for priority, patterns in pattern_groups:
        for pattern in patterns:
            for match in re.finditer(pattern, lower):
                score = _score_section_match(full_text, match, priority)
                if score < 0:
                    continue
                start = match.start()
                end = min(len(full_text), match.start() + _SECTION_WINDOW_AFTER)
                candidates.append((score, start, end))

    if not candidates:
        return []

    candidates.sort(key=lambda x: x[0], reverse=True)
    chosen: list[tuple[int, int]] = []
    for _, start, end in candidates:
        if any(not (end < s or start > e) for s, e in chosen):
            continue
        chosen.append((start, end))
        if len(chosen) >= 3:
            break

    chosen.sort(key=lambda s: s[0])
    return [full_text[s:e].strip() for s, e in chosen]


def _merge_gap_text(page_gap: str, span_gaps: list[str]) -> str:
    """Combina extração por página e por span, priorizando o mais completo."""
    parts: list[str] = []
    if page_gap.strip():
        parts.append(page_gap.strip())
    for section in span_gaps:
        if section.strip() and section.strip() not in parts:
            parts.append(section.strip())
    return "\n\n---\n\n".join(parts)


def _build_extraction_text(full_text: str, pages: list[str]) -> str:
    """
    Monta texto para o LLM. As seções de lacunas têm orçamento reservado e não são cortadas primeiro.
    """
    if len(full_text) <= MAX_TEXT_CHARS:
        return full_text

    gap_text = _merge_gap_text(_extract_gap_text_from_pages(pages), _extract_gap_sections(full_text))

    chunks: list[str] = []
    budget = MAX_TEXT_CHARS

    if gap_text:
        gap_chunk = (
            "=== LIMITAÇÕES, LACUNAS E SUGESTÕES (texto completo da seção no documento) ===\n"
            + gap_text
        )
        if len(gap_chunk) > _GAP_BUDGET:
            gap_chunk = gap_chunk[:_GAP_BUDGET]
        chunks.append(gap_chunk)
        budget -= len(gap_chunk) + 4

    tail_budget = min(_TAIL_CHARS, budget // 3)
    head_budget = min(_HEAD_CHARS, budget - tail_budget - 100)
    tail_budget = min(tail_budget, budget - head_budget - 100)

    if head_budget > 500:
        chunks.insert(
            0,
            f"=== INÍCIO DO DOCUMENTO ===\n{full_text[:head_budget]}",
        )
    if tail_budget > 500:
        chunks.append(f"=== FINAL DO DOCUMENTO ===\n{full_text[-tail_budget:]}")

    combined = "\n\n".join(chunks)
    if len(combined) <= MAX_TEXT_CHARS:
        return combined

    gap_chunk = next((c for c in chunks if "LIMITAÇÕES, LACUNAS" in c), "")
    if gap_chunk:
        other_chunks = [c for c in chunks if c is not gap_chunk]
        room = MAX_TEXT_CHARS - len(gap_chunk) - 4
        trimmed: list[str] = []
        for chunk in other_chunks:
            if room <= 0:
                break
            if len(chunk) <= room:
                trimmed.append(chunk)
                room -= len(chunk) + 4
            elif room > 400:
                trimmed.append(chunk[:room])
                room = 0
        return "\n\n".join(trimmed + [gap_chunk])

    return combined[:MAX_TEXT_CHARS]


async def extract_single_pdf(filename: str, content: bytes) -> PDFPaperResult:
    pages = _extract_pdf_pages(content)
    full_text = "\n".join(pages)

    if not full_text.strip():
        return PDFPaperResult(
            filename=filename,
            title=filename.removesuffix(".pdf").replace("_", " ").replace("-", " "),
            error="Não foi possível extrair texto deste PDF (protegido ou escaneado sem OCR).",
        )

    gap_page_text = _extract_gap_text_from_pages(pages)
    gap_span_text = _merge_gap_text("", _extract_gap_sections(full_text))
    has_gap_content = bool(gap_page_text.strip() or gap_span_text.strip())

    text = _build_extraction_text(full_text, pages)
    gap_hint = (
        "Foi localizada a seção de limitações/lacunas no corpo do documento (não apenas no sumário). "
        "O bloco 'LIMITAÇÕES, LACUNAS E SUGESTÕES' contém o texto dessa seção."
        if has_gap_content
        else "Nenhuma seção explícita de limitações foi localizada; use Conclusão/Discussão no trecho final."
    )

    user_prompt = (
        f"Nome do arquivo: {filename}\n"
        f"Páginas: {len(pages)} · Tamanho total: ~{len(full_text)} caracteres\n"
        f"Nota: {gap_hint}\n\n"
        f"Texto selecionado para análise:\n{text}\n\n"
        "Instrução extra: extraia o campo gaps a partir do bloco de LIMITAÇÕES/LACUNAS quando presente. "
        "Liste cada limitação e sugestão declarada pelos autores."
    )

    try:
        raw = await call_llm(PDF_EXTRACTION_SYSTEM, user_prompt)
        data = parse_extraction_response(raw)
    except Exception as exc:
        logger.error("LLM extraction failed for %s: %s", filename, exc)
        return PDFPaperResult(
            filename=filename,
            title=filename.removesuffix(".pdf"),
            error=f"Erro na extração via LLM: {exc}",
        )

    authors = data.get("authors", [])
    if not isinstance(authors, list):
        authors = [str(authors)] if authors else []

    year = data.get("year")
    if isinstance(year, str):
        try:
            year = int(year[:4])
        except (ValueError, TypeError):
            year = None

    citations: list[CitationSpan] = []
    for c in data.get("citations", []):
        if isinstance(c, dict):
            citations.append(
                CitationSpan(
                    field=c.get("field", ""),
                    text=c.get("text", ""),
                    source_text=c.get("source_text", ""),
                )
            )

    return PDFPaperResult(
        filename=filename,
        title=data.get("title") or filename.removesuffix(".pdf"),
        authors=[str(a) for a in authors if a],
        year=year,
        objectives=data.get("objectives"),
        methodology=data.get("methodology"),
        results=data.get("results"),
        gaps=data.get("gaps"),
        citations=citations,
    )


async def analyze_correlations(
    papers: list[PDFPaperResult],
) -> tuple[list[CorrelationInsight], str]:
    if len(papers) < 2:
        return [], "Análise de correlações requer pelo menos 2 trabalhos."

    summaries: list[str] = []
    for p in papers:
        if p.error:
            continue
        parts = [f"Trabalho: {p.title}"]
        if p.objectives:
            parts.append(f"  Objetivos: {p.objectives[:400]}")
        if p.methodology:
            parts.append(f"  Metodologia: {p.methodology[:300]}")
        if p.results:
            parts.append(f"  Resultados: {p.results[:400]}")
        if p.gaps:
            parts.append(f"  Lacunas: {p.gaps[:600]}")
        summaries.append("\n".join(parts))

    if not summaries:
        return [], "Nenhum trabalho com dados extraídos para correlacionar."

    user_prompt = (
        f"Analise os {len(summaries)} trabalhos acadêmicos abaixo e identifique "
        f"correlações, padrões e insights para revisão de tese:\n\n"
        + "\n\n---\n\n".join(summaries)
    )

    try:
        raw = await call_llm(CORRELATION_SYSTEM, user_prompt)
        data = parse_extraction_response(raw)
    except Exception as exc:
        logger.error("Correlation LLM failed: %s", exc)
        return [], f"Erro na análise de correlações: {exc}"

    insights: list[CorrelationInsight] = []
    for c in data.get("correlations", []):
        if not isinstance(c, dict):
            continue
        linked = c.get("papers", [])
        insights.append(
            CorrelationInsight(
                category=c.get("category", "insights"),
                title=c.get("title", ""),
                description=c.get("description", ""),
                papers=linked if isinstance(linked, list) else [],
            )
        )

    narrative = data.get("narrative") or ""
    return insights, narrative
