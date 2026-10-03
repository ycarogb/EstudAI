from app.extraction.llm import call_llm, fetch_pdf_text, get_source_text, parse_extraction_response
from app.models.schemas import (
    MENDELEY_EXTRACTION_FIELDS,
    TEXT_SOURCE_LABELS,
    CitationSpan,
    CollectionAnalysisResponse,
    Paper,
    TextSource,
)

EXTRACTION_SYSTEM = """Você é um assistente de revisão bibliográfica acadêmica.
Analise o texto fornecido e extraia informações estruturadas em português.
O texto pode ser em inglês ou português.
Responda APENAS com JSON válido no formato:
{
  "objectives": "objetivos da pesquisa",
  "results": "principais resultados encontrados",
  "gaps": "lacunas, limitações ou sugestões de pesquisa futura declaradas pelos autores",
  "methods": "métodos, técnicas e abordagens metodológicas utilizadas",
  "scope": "escopo temático do trabalho (o que abrange e o que exclui)",
  "geographic_scope": "recorte geográfico, populacional ou contextual (país, região, instituição)",
  "cited_references": ["referência 1 citada no texto", "referência 2"],
  "citations": [
    {"field": "objectives|results|gaps|methods|scope|geographic_scope", "text": "resumo", "source_text": "trecho literal"}
  ]
}
Para cited_references, todas as referências bibliográficas mencionadas no texto (autor + ano ou título).
Se alguma informação não estiver disponível, use null ou [].
Cite trechos literais do texto fonte sempre que possível."""

_SOURCE_QUALITY_LABEL: dict[str, str] = {
    TextSource.PDF_LOCAL: "texto completo do PDF (análise aprofundada)",
    TextSource.PDF_OPEN: "texto completo do PDF de acesso aberto (análise aprofundada)",
    TextSource.ABSTRACT: "somente o resumo (abstract) — análise parcial",
    TextSource.CROSSREF_ABSTRACT: "somente o resumo via Crossref — análise parcial",
    TextSource.METADATA_ONLY: "apenas metadados (título e autores) — análise muito limitada",
}

LIST_FIELDS = {"cited_references"}


class Extractor:
    def _apply_extraction(self, paper: Paper, data: dict, fields: list[str]) -> Paper:
        for field in fields:
            if field in LIST_FIELDS:
                value = data.get(field, [])
                if isinstance(value, list):
                    paper.cited_references = [str(v) for v in value if v]
            elif hasattr(paper, field):
                setattr(paper, field, data.get(field))

        citations = []
        for c in data.get("citations", []):
            if isinstance(c, dict):
                citations.append(
                    CitationSpan(
                        field=c.get("field", ""),
                        text=c.get("text", ""),
                        source_text=c.get("source_text", ""),
                    )
                )
        paper.citations = citations
        return paper

    async def extract_paper(
        self,
        paper: Paper,
        fields: list[str] | None = None,
        pdf_text: str | None = None,
    ) -> Paper:
        fields = fields or ["objectives", "results", "gaps"]

        if pdf_text is None and paper.pdf_url:
            pdf_text = await fetch_pdf_text(paper.pdf_url)

        source_text = get_source_text(paper.abstract, pdf_text)
        if not source_text or len(source_text.strip()) < 80:
            paper.gaps = paper.gaps or (
                "Texto insuficiente: exporte o PDF do Mendeley e use «Anexar PDFs» antes de analisar."
            )
            return paper

        # Indicar ao LLM a qualidade da fonte
        source_quality = _SOURCE_QUALITY_LABEL.get(
            paper.text_source or "", "texto disponível"
        )

        user_prompt = f"""Título: {paper.title}
Autores: {', '.join(paper.authors[:5])}
Ano: {paper.year or 'N/A'}
Fonte para análise: {source_quality}

Texto para análise:
{source_text[:12000]}

Extraia: {', '.join(fields)}"""

        raw = await call_llm(EXTRACTION_SYSTEM, user_prompt)
        data = parse_extraction_response(raw)
        return self._apply_extraction(paper, data, fields)

    async def extract_batch(
        self,
        papers: list[Paper],
        fields: list[str] | None = None,
        limit: int | None = None,
    ) -> list[Paper]:
        batch = papers[:limit] if limit else papers
        results = []
        for paper in batch:
            results.append(await self.extract_paper(paper, fields))
        return results

    async def synthesize_gaps(self, papers: list[Paper]) -> dict:
        gaps_text = []
        for p in papers:
            if p.gaps:
                gaps_text.append(f"- {p.title}: {p.gaps}")

        if not gaps_text:
            return {
                "summary": "Nenhuma lacuna extraída ainda. Execute a extração nos papers primeiro.",
                "gaps": [],
                "themes": [],
            }

        user_prompt = f"""Com base nas lacunas identificadas nos trabalhos abaixo, produza uma síntese para fundamentar uma proposta de tese.

Lacunas por trabalho:
{chr(10).join(gaps_text[:30])}

Responda em JSON:
{{
  "summary": "síntese narrativa das lacunas no estado da arte",
  "gaps": ["lacuna 1", "lacuna 2"],
  "themes": ["tema recorrente 1", "tema recorrente 2"]
}}"""

        raw = await call_llm(
            "Você sintetiza lacunas de pesquisa para propostas de tese. Responda apenas JSON.",
            user_prompt,
        )
        data = parse_extraction_response(raw)
        return {
            "summary": data.get("summary", raw[:1000]),
            "gaps": data.get("gaps", []) if isinstance(data.get("gaps"), list) else [],
            "themes": data.get("themes", []) if isinstance(data.get("themes"), list) else [],
        }

    async def synthesize_collection(self, analysis: CollectionAnalysisResponse) -> str:
        shared = "\n".join(
            f"- {r.reference} (citada em {r.count} trabalhos)"
            for r in analysis.shared_references[:15]
        )
        gaps = "\n".join(f"- {g}" for g in analysis.gaps_summary[:10])
        methods = "\n".join(f"- {m}" for m in analysis.methods_summary[:10])

        # breakdown de fontes
        breakdown_lines = []
        for src, count in (analysis.text_source_breakdown or {}).items():
            label = TEXT_SOURCE_LABELS.get(src, src)
            breakdown_lines.append(f"  {label}: {count}")
        breakdown_text = "\n".join(breakdown_lines) or "  N/A"

        prompt = f"""Sintetize esta coleção bibliográfica importada do Mendeley para revisão de tese.

Total de trabalhos: {analysis.total_papers}
Fontes de análise utilizadas:
{breakdown_text}

Lacunas identificadas:
{gaps or 'Nenhuma'}

Métodos recorrentes:
{methods or 'Nenhum'}

Referências citadas em múltiplos trabalhos:
{shared or 'Nenhuma'}

Escopos: {', '.join(analysis.scopes_summary[:5]) or 'N/A'}
Recortes geográficos: {', '.join(analysis.geographic_scopes_summary[:5]) or 'N/A'}

Produza um parágrafo narrativo em português (4-6 frases) destacando lacunas, convergências metodológicas e referências centrais da coleção."""

        return await call_llm(
            "Você é um orientador de pós-graduação auxiliando na revisão bibliográfica.",
            prompt,
        )

    async def analyze_mendeley_collection(
        self, papers: list[Paper], limit: int = 25
    ) -> tuple[list[Paper], CollectionAnalysisResponse]:
        from app.analysis.collection import (
            analyze_paper_relationships,
            build_collection_summary,
            build_text_source_breakdown,
            find_shared_references,
        )
        from app.enrichment.paper_enricher import enrich_papers

        # 1. Enriquecer: buscar DOI/abstract via Crossref, OpenAlex, S2
        enriched, coverage = await enrich_papers(papers)

        # 2. Extrair campos via LLM (com fonte indicada no prompt)
        extracted = await self.extract_batch(
            enriched, fields=MENDELEY_EXTRACTION_FIELDS, limit=limit
        )
        paper_map = {p.id: p for p in extracted}
        updated = [paper_map.get(p.id, p) for p in enriched]
        for ep in extracted:
            if ep.id not in {p.id for p in enriched}:
                updated.append(ep)

        # 3. Construir análise da coleção
        breakdown = build_text_source_breakdown(updated)
        shared = find_shared_references(updated)
        analysis = build_collection_summary(updated, shared, breakdown)
        analysis.papers_with_text = coverage["with_text"]
        analysis.papers_without_text = coverage["without_text"]
        analysis.coverage_percent = coverage["coverage_percent"]
        analysis.text_source_breakdown = coverage.get("text_source_breakdown", breakdown)
        analysis.analyzed_papers = sum(
            1 for p in extracted
            if not (p.gaps or "").startswith("Texto insuficiente")
        )

        # 4. Correlações e relações entre os trabalhos
        correlations, correlation_narrative = await analyze_paper_relationships(updated)
        analysis.correlations = correlations

        # 5. Síntese narrativa (incorpora info de fonte + correlações)
        analysis.narrative_summary = await self.synthesize_collection(analysis)

        # Se tiver narrativa de correlações e não houver narrativa principal ainda, usar ela
        if not analysis.narrative_summary and correlation_narrative:
            analysis.narrative_summary = correlation_narrative

        return updated, analysis


extractor = Extractor()
