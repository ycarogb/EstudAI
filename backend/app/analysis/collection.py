"""
Funções de análise de coleção bibliográfica:
- Referências compartilhadas
- Breakdown de fontes textuais
- Correlações e relações entre papers via LLM (reaproveitável em qualquer fluxo)
"""

import logging
from collections import defaultdict

from app.extraction.llm import call_llm, parse_extraction_response
from app.models.schemas import (
    CollectionAnalysisResponse,
    CorrelationInsight,
    Paper,
    SharedReference,
    TEXT_SOURCE_LABELS,
)
from app.search.base import normalize_title

logger = logging.getLogger(__name__)

CORRELATION_SYSTEM = """Você é especialista em síntese de literatura científica para revisão sistemática de tese.
Analise os dados extraídos de múltiplos trabalhos e identifique padrões e correlações.
Responda APENAS com JSON no formato:
{
  "correlations": [
    {
      "category": "conclusoes_comuns|lacunas_comuns|padroes_metodologicos|divergencias|tendencias|insights",
      "title": "Título conciso do insight",
      "description": "Descrição detalhada em 2-4 frases explicando o padrão, quais trabalhos compartilham e sua implicação para a pesquisa",
      "papers": ["Título do trabalho 1", "Título do trabalho 2"]
    }
  ],
  "narrative": "Síntese narrativa em 4-6 frases descrevendo o estado da arte evidenciado pela coleção e as principais oportunidades de pesquisa identificadas"
}
Gere pelo menos um insight por categoria disponível. Foque nos padrões mais relevantes para construção de proposta de tese."""


def _ref_key(reference: str) -> str:
    return normalize_title(reference)[:100]


def find_shared_references(papers: list[Paper]) -> list[SharedReference]:
    """Identifica referências citadas em mais de um trabalho da coleção."""
    ref_map: dict[str, dict] = defaultdict(lambda: {"label": "", "papers": []})

    for paper in papers:
        for ref in paper.cited_references or []:
            ref = ref.strip()
            if len(ref) < 8:
                continue
            key = _ref_key(ref)
            if not ref_map[key]["label"]:
                ref_map[key]["label"] = ref
            ref_map[key]["papers"].append(
                {"id": paper.id, "title": paper.title, "year": paper.year}
            )

    shared = []
    for entry in ref_map.values():
        if len(entry["papers"]) >= 2:
            shared.append(
                SharedReference(
                    reference=entry["label"],
                    count=len(entry["papers"]),
                    papers=entry["papers"],
                )
            )

    shared.sort(key=lambda r: r.count, reverse=True)
    return shared


def build_text_source_breakdown(papers: list[Paper]) -> dict[str, int]:
    """Contagem de papers por tipo de fonte textual."""
    from collections import Counter
    from app.models.schemas import TextSource
    return dict(Counter(p.text_source or TextSource.METADATA_ONLY for p in papers))


def build_collection_summary(
    papers: list[Paper],
    shared_refs: list[SharedReference],
    text_source_breakdown: dict[str, int] | None = None,
) -> CollectionAnalysisResponse:
    gaps = [p.gaps for p in papers if p.gaps]
    methods = list({p.methods for p in papers if p.methods})
    scopes = list({p.scope for p in papers if p.scope})
    geo_scopes = list({p.geographic_scope for p in papers if p.geographic_scope})

    return CollectionAnalysisResponse(
        total_papers=len(papers),
        analyzed_papers=sum(
            1 for p in papers if any([p.gaps, p.methods, p.scope, p.geographic_scope])
        ),
        gaps_summary=gaps[:20],
        methods_summary=methods[:15],
        scopes_summary=scopes[:15],
        geographic_scopes_summary=geo_scopes[:15],
        shared_references=shared_refs,
        text_source_breakdown=text_source_breakdown or {},
    )


async def analyze_paper_relationships(
    papers: list[Paper],
) -> tuple[list[CorrelationInsight], str]:
    """
    Análise LLM de correlações e relações entre Papers.
    Retorna (lista de CorrelationInsight, narrativa textual).
    Funciona com papers de qualquer fonte (Mendeley, busca, etc.).
    """
    analyzable = [
        p for p in papers
        if any([p.objectives, p.results, p.gaps, p.methods, p.abstract])
    ]

    if len(analyzable) < 2:
        return [], "Análise de correlações requer pelo menos 2 trabalhos com conteúdo extraído."

    summaries: list[str] = []
    for p in analyzable:
        source_label = TEXT_SOURCE_LABELS.get(p.text_source or "", "")
        parts = [f"Trabalho: {p.title}"]
        if p.year:
            parts.append(f"  Ano: {p.year}")
        if source_label:
            parts.append(f"  Fonte da análise: {source_label}")
        if p.objectives:
            parts.append(f"  Objetivos: {p.objectives[:400]}")
        if p.methods:
            parts.append(f"  Métodos: {p.methods[:300]}")
        if p.results:
            parts.append(f"  Resultados: {p.results[:400]}")
        if p.gaps:
            parts.append(f"  Lacunas: {p.gaps[:300]}")
        elif p.abstract and not p.objectives:
            parts.append(f"  Resumo: {p.abstract[:500]}")
        summaries.append("\n".join(parts))

    user_prompt = (
        f"Analise os {len(summaries)} trabalhos acadêmicos abaixo e identifique "
        f"correlações, padrões e insights para revisão de tese:\n\n"
        + "\n\n---\n\n".join(summaries[:40])
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
