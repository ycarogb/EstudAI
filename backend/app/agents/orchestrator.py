import json
import re
from datetime import datetime

from app.agents.prompts import CHAT_SYSTEM, QUERY_EXPANSION_SYSTEM
from app.extraction.extractor import extractor
from app.extraction.llm import call_llm, parse_extraction_response
from app.extraction.llm_config import LLMNotConfiguredError
from app.models.schemas import MENDELEY_EXTRACTION_FIELDS, Paper, SearchFilters
from app.search.hub import search_hub


class AgentOrchestrator:
    async def expand_query(self, natural_language: str) -> dict:
        try:
            raw = await call_llm(
                QUERY_EXPANSION_SYSTEM,
                f"Tema de pesquisa: {natural_language}",
            )
        except LLMNotConfiguredError:
            raw = "{}"
        data = parse_extraction_response(raw)

        year_from = data.get("year_from")
        year_to = data.get("year_to")

        if isinstance(year_from, str) and year_from.isdigit():
            year_from = int(year_from)
        if isinstance(year_to, str) and year_to.isdigit():
            year_to = int(year_to)

        return {
            "search_query": data.get("search_query", natural_language),
            "keywords_pt": data.get("keywords_pt", []),
            "keywords_en": data.get("keywords_en", []),
            "year_from": year_from,
            "year_to": year_to,
            "summary": data.get("summary", ""),
        }

    def _detect_intent(self, message: str) -> str:
        lower = message.lower()
        if any(w in lower for w in ["extraia", "extrair", "objetivos", "resultados", "lacunas", "métodos", "metodos", "escopo"]):
            return "extract"
        if any(w in lower for w in ["analis", "coleção", "colecao", "mendeley"]):
            return "analyze"
        if any(w in lower for w in ["sintetize", "síntese", "mapa de lacunas", "lacunas do estado"]):
            return "synthesize"
        if any(w in lower for w in ["filtre", "filtro", "últimos", "ultimos", "apenas", "somente"]):
            return "filter"
        if any(w in lower for w in ["busque", "buscar", "encontre", "procure", "artigos", "teses"]):
            return "search"
        return "search"

    def _parse_year_filter(self, message: str) -> tuple[int | None, int | None]:
        year_from = None
        year_to = None
        current_year = datetime.now().year

        last_n = re.search(r"últimos?\s+(\d+)\s+anos?", message, re.I)
        if last_n:
            n = int(last_n.group(1))
            year_from = current_year - n

        from_match = re.search(r"(?:a partir de|desde)\s+(\d{4})", message, re.I)
        if from_match:
            year_from = int(from_match.group(1))

        to_match = re.search(r"(?:até|antes de)\s+(\d{4})", message, re.I)
        if to_match:
            year_to = int(to_match.group(1))

        return year_from, year_to

    async def process_message(
        self,
        message: str,
        papers: list[Paper] | None = None,
    ) -> dict:
        intent = self._detect_intent(message)
        papers = papers or []

        if intent == "extract" and papers:
            fields = []
            lower = message.lower()
            if "objetivo" in lower:
                fields.append("objectives")
            if "resultado" in lower:
                fields.append("results")
            if "lacuna" in lower or "gap" in lower:
                fields.append("gaps")
            if "método" in lower or "metodo" in lower:
                fields.append("methods")
            if "escopo" in lower:
                fields.append("scope")
            if "geográf" in lower or "geograf" in lower or "recorte" in lower:
                fields.append("geographic_scope")
            if not fields:
                fields = MENDELEY_EXTRACTION_FIELDS

            extracted = await extractor.extract_batch(papers[:10], fields)
            paper_map = {p.id: p for p in extracted}
            updated = [paper_map.get(p.id, p) for p in papers]
            for ep in extracted:
                if ep.id not in {p.id for p in papers}:
                    updated.append(ep)

            reply = f"Extraí {len(extracted)} trabalho(s) com os campos solicitados."
            return {"reply": reply, "papers": updated, "action": "extract"}

        if intent == "analyze" and papers:
            updated, analysis = await extractor.analyze_mendeley_collection(papers)
            reply = analysis.narrative_summary or "Análise da coleção concluída."
            return {
                "reply": reply,
                "papers": updated,
                "action": "analyze",
                "analysis": analysis.model_dump(mode="json"),
            }

        if intent == "synthesize" and papers:
            with_gaps = [p for p in papers if p.gaps]
            if not with_gaps:
                papers = await extractor.extract_batch(papers[:15], ["gaps"])
            synthesis = await extractor.synthesize_gaps(papers)
            reply = synthesis.get("summary", "Síntese gerada.")
            return {
                "reply": reply,
                "papers": papers,
                "action": "synthesize",
                "synthesis": synthesis,
            }

        year_from, year_to = self._parse_year_filter(message)
        expanded = await self.expand_query(message)

        filters = SearchFilters(
            year_from=year_from or expanded.get("year_from"),
            year_to=year_to or expanded.get("year_to"),
            limit=25,
        )

        query = expanded.get("search_query", message)
        results = await search_hub.search(query, filters)

        if intent == "filter" and papers:
            filtered = papers
            if year_from:
                filtered = [p for p in filtered if p.year is None or p.year >= year_from]
            if year_to:
                filtered = [p for p in filtered if p.year is None or p.year <= year_to]
            reply = f"Filtrei para {len(filtered)} trabalho(s)."
            return {"reply": reply, "papers": filtered, "action": "filter"}

        summary = expanded.get("summary", "")
        try:
            reply = await call_llm(
                CHAT_SYSTEM,
                f"""O usuário perguntou: {message}

Encontrei {len(results)} trabalhos relacionados.
Query usada: {query}
{summary}

Gere uma resposta breve (2-3 frases) apresentando os resultados.""",
            )
        except LLMNotConfiguredError:
            reply = f"Encontrei {len(results)} trabalho(s) para \"{query}\"."

        return {
            "reply": reply,
            "papers": results,
            "action": "search",
            "query_used": query,
        }


orchestrator = AgentOrchestrator()
