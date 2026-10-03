import json
import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import PlainTextResponse, Response, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.orchestrator import orchestrator
from app.db.database import get_db
from app.db.models import ChatMessage, Project, ProjectPaper
from app.extraction.extractor import extractor
from app.extraction.llm import call_llm
from app.extraction.llm_config import (
    DEFAULT_MODELS,
    SUPPORTED_PROVIDERS,
    LLMNotConfiguredError,
    current_llm_config,
    is_llm_configured,
    ollama_configured,
    server_llm_config,
)
from app.importers.mendeley import parse_mendeley_export
from app.importers.pdf_attach import attach_pdfs_to_papers
from app.importers.ris_bibtex import parse_import_file, papers_to_bibtex, papers_to_csv
from app.models.schemas import (
    ChatRequest,
    ChatResponse,
    CollectionAnalysisResponse,
    ExtractRequest,
    ExtractResponse,
    MAX_PDF_FILES,
    Paper,
    PdfAnalysisChatPersistRequest,
    PdfAnalysisChatRequest,
    PdfAnalysisChatResponse,
    PdfAnalysisCreate,
    PdfAnalysisDetail,
    PdfAnalysisExportRequest,
    PdfAnalysisSummary,
    ProjectCreate,
    ProjectResponse,
    SearchFilters,
    SearchRequest,
    SearchResponse,
    SynthesisResponse,
)
from app.search.hub import search_hub

router = APIRouter()
logger = logging.getLogger(__name__)


def require_llm() -> None:
    if not is_llm_configured():
        raise LLMNotConfiguredError()


def paper_from_db(row: ProjectPaper) -> Paper:
    return Paper(**row.paper_data)


def paper_to_dict(paper: Paper) -> dict:
    return paper.model_dump(mode="json")


@router.get("/sources")
async def list_sources():
    from app.config import settings

    return {
        "sources": [
            {"id": "openalex", "name": "OpenAlex", "enabled": True, "type": "open"},
            {"id": "semantic_scholar", "name": "Semantic Scholar", "enabled": True, "type": "open"},
            {"id": "bdtd", "name": "BDTD", "enabled": True, "type": "open"},
            {"id": "scielo", "name": "SciELO", "enabled": True, "type": "open"},
            {
                "id": "google_scholar",
                "name": "Google Scholar",
                "enabled": bool(settings.serpapi_api_key),
                "type": "paid",
                "note": "Configure SERPAPI_API_KEY no .env (via SerpApi)",
            },
            {"id": "import", "name": "Importação CAPES (RIS/BibTeX)", "enabled": True, "type": "import"},
            {"id": "mendeley", "name": "Coleção Mendeley (BibTeX/RIS)", "enabled": True, "type": "import"},
            {
                "id": "scopus",
                "name": "Scopus",
                "enabled": bool(settings.scopus_api_key),
                "type": "paid",
                "note": "Configure SCOPUS_API_KEY no .env",
            },
            {
                "id": "wos",
                "name": "Web of Science",
                "enabled": bool(settings.wos_api_key),
                "type": "paid",
                "note": "Configure WOS_API_KEY no .env",
            },
        ]
    }


@router.get("/health")
async def health():
    return {"status": "ok", "service": "estudai"}


@router.get("/llm/status")
async def llm_status():
    """Informa se o servidor tem uma chave padrão (sem expor a chave)."""
    server = server_llm_config()
    return {
        "server_configured": server is not None or ollama_configured(),
        "server_provider": server.provider if server else None,
        "server_model": server.model if server else None,
        "supported_providers": list(SUPPORTED_PROVIDERS),
        "default_models": DEFAULT_MODELS,
    }


def _describe_llm_error(exc: Exception) -> str:
    status = getattr(exc, "status_code", None)
    if status in (401, 403) or "api key" in str(exc).lower():
        return "Chave de API inválida ou sem permissão para este provedor."
    if status == 404:
        return "Modelo não encontrado neste provedor. Confira o nome do modelo."
    if status == 429:
        return "Limite de uso atingido ou créditos esgotados neste provedor."
    return f"Não foi possível conectar ao provedor: {exc}"


@router.post("/llm/test", dependencies=[Depends(require_llm)])
async def llm_test():
    """Valida a chave informada fazendo uma chamada mínima ao provedor."""
    config = current_llm_config()
    try:
        await call_llm("Responda apenas com a palavra OK.", "Teste de conexão.")
    except Exception as exc:
        raise HTTPException(400, _describe_llm_error(exc)) from exc
    return {
        "ok": True,
        "provider": config.provider if config else "ollama",
        "model": config.model if config else None,
    }


@router.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    expanded = await orchestrator.expand_query(request.query)
    query = expanded.get("search_query", request.query)
    filters = request.filters
    if expanded.get("year_from") and not filters.year_from:
        filters.year_from = expanded["year_from"]
    if expanded.get("year_to") and not filters.year_to:
        filters.year_to = expanded["year_to"]

    papers = await search_hub.search(query, filters)
    return SearchResponse(papers=papers, total=len(papers), query_used=query)


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    existing_papers: list[Paper] = []
    project_id = request.project_id

    if project_id:
        result = await db.execute(
            select(Project)
            .where(Project.id == project_id)
            .options(selectinload(Project.papers))
        )
        project = result.scalar_one_or_none()
        if project:
            existing_papers = [paper_from_db(p) for p in project.papers]

    response = await orchestrator.process_message(request.message, existing_papers)

    if not project_id and response.get("papers"):
        project = Project(
            title=request.message[:100],
            query=request.message,
        )
        db.add(project)
        await db.flush()
        project_id = project.id

        for paper in response["papers"]:
            db.add(
                ProjectPaper(
                    project_id=project_id,
                    paper_id=paper.id,
                    paper_data=paper_to_dict(paper),
                    relevance_score=paper.relevance_score,
                )
            )
    elif project_id and response.get("papers"):
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if project:
            if response.get("action") == "search":
                await db.execute(
                    ProjectPaper.__table__.delete().where(ProjectPaper.project_id == project_id)
                )
                for paper in response["papers"]:
                    db.add(
                        ProjectPaper(
                            project_id=project_id,
                            paper_id=paper.id,
                            paper_data=paper_to_dict(paper),
                            relevance_score=paper.relevance_score,
                        )
                    )
            elif response.get("action") in ("extract", "filter", "synthesize", "analyze"):
                for paper in response["papers"]:
                    result = await db.execute(
                        select(ProjectPaper).where(
                            ProjectPaper.project_id == project_id,
                            ProjectPaper.paper_id == paper.id,
                        )
                    )
                    row = result.scalar_one_or_none()
                    if row:
                        row.paper_data = paper_to_dict(paper)
                    else:
                        db.add(
                            ProjectPaper(
                                project_id=project_id,
                                paper_id=paper.id,
                                paper_data=paper_to_dict(paper),
                            )
                        )

            if response.get("action") == "analyze" and response.get("analysis"):
                project.analysis_data = response["analysis"]

    if project_id:
        db.add(ChatMessage(project_id=project_id, role="user", content=request.message))
        db.add(
            ChatMessage(
                project_id=project_id,
                role="assistant",
                content=response["reply"],
                metadata_={"action": response.get("action")},
            )
        )

    await db.commit()

    return ChatResponse(
        reply=response["reply"],
        papers=response.get("papers", []),
        project_id=project_id,
        action=response.get("action"),
    )


@router.post("/extract", response_model=ExtractResponse, dependencies=[Depends(require_llm)])
async def extract(request: ExtractRequest, db: AsyncSession = Depends(get_db)):
    papers = [Paper(**p) for p in []]
    if not request.paper_ids:
        raise HTTPException(400, "paper_ids required")

    for pid in request.paper_ids:
        result = await db.execute(
            select(ProjectPaper).where(ProjectPaper.paper_id == pid).limit(1)
        )
        row = result.scalar_one_or_none()
        if row:
            papers.append(paper_from_db(row))

    if not papers:
        raise HTTPException(404, "Papers not found")

    extracted = await extractor.extract_batch(papers, request.fields)
    return ExtractResponse(papers=extracted)


@router.post("/projects", response_model=ProjectResponse)
async def create_project(data: ProjectCreate, db: AsyncSession = Depends(get_db)):
    project = Project(title=data.title, query=data.query)
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return ProjectResponse(
        id=project.id,
        title=project.title,
        query=project.query,
        created_at=project.created_at.isoformat(),
        paper_count=0,
    )


@router.get("/projects", response_model=list[ProjectResponse])
async def list_projects(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Project).options(selectinload(Project.papers)).order_by(Project.updated_at.desc())
    )
    projects = result.scalars().all()
    return [
        ProjectResponse(
            id=p.id,
            title=p.title,
            query=p.query,
            created_at=p.created_at.isoformat(),
            paper_count=len(p.papers),
        )
        for p in projects
    ]


@router.get("/projects/{project_id}")
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Project)
        .where(Project.id == project_id)
        .options(selectinload(Project.papers), selectinload(Project.messages))
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Project not found")

    return {
        "id": project.id,
        "title": project.title,
        "query": project.query,
        "created_at": project.created_at.isoformat(),
        "papers": [paper_from_db(p).model_dump(mode="json") for p in project.papers],
        "analysis": project.analysis_data,
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at.isoformat(),
            }
            for m in project.messages
        ],
    }


@router.patch("/projects/{project_id}/papers/{paper_id}")
async def toggle_paper_selection(
    project_id: str, paper_id: str, selected: bool = True, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(ProjectPaper).where(
            ProjectPaper.project_id == project_id,
            ProjectPaper.paper_id == paper_id,
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(404, "Paper not found")
    row.selected = selected
    await db.commit()
    return {"ok": True}


@router.post("/projects/{project_id}/import")
async def import_references(
    project_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Project not found")

    content = (await file.read()).decode("utf-8", errors="replace")
    papers = parse_import_file(file.filename or "import.ris", content)

    for paper in papers:
        db.add(
            ProjectPaper(
                project_id=project_id,
                paper_id=paper.id,
                paper_data=paper_to_dict(paper),
            )
        )

    await db.commit()
    return {"imported": len(papers), "papers": [p.model_dump(mode="json") for p in papers]}


@router.post("/projects/{project_id}/import-mendeley")
async def import_mendeley_collection(
    project_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Project not found")

    content = (await file.read()).decode("utf-8", errors="replace")
    papers = parse_mendeley_export(file.filename or "mendeley.bib", content)

    if not papers:
        raise HTTPException(400, "Nenhuma referência encontrada no arquivo Mendeley.")

    for paper in papers:
        existing = await db.execute(
            select(ProjectPaper).where(
                ProjectPaper.project_id == project_id,
                ProjectPaper.paper_id == paper.id,
            )
        )
        if existing.scalar_one_or_none():
            continue
        db.add(
            ProjectPaper(
                project_id=project_id,
                paper_id=paper.id,
                paper_data=paper_to_dict(paper),
            )
        )

    await db.commit()

    result = await db.execute(
        select(ProjectPaper).where(ProjectPaper.project_id == project_id)
    )
    all_papers = [paper_from_db(r) for r in result.scalars().all()]

    return {
        "imported": len(papers),
        "papers": [p.model_dump(mode="json") for p in all_papers],
        "message": f"Importados {len(papers)} trabalho(s). Clique em «Analisar coleção» para iniciar a análise.",
    }


@router.post("/projects/{project_id}/upload-pdfs")
async def upload_pdfs(
    project_id: str,
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ProjectPaper).where(ProjectPaper.project_id == project_id)
    )
    rows = result.scalars().all()
    if not rows:
        raise HTTPException(404, "Nenhum trabalho no projeto.")

    papers = [paper_from_db(r) for r in rows]
    pdf_files: list[tuple[str, bytes]] = []
    for f in files:
        if f.filename and f.filename.lower().endswith(".pdf"):
            pdf_files.append((f.filename, await f.read()))

    if not pdf_files:
        raise HTTPException(400, "Envie arquivos PDF.")

    updated, unmatched = await attach_pdfs_to_papers(papers, pdf_files)
    paper_map = {p.id: p for p in updated}
    for row in rows:
        if row.paper_id in paper_map:
            row.paper_data = paper_to_dict(paper_map[row.paper_id])

    await db.commit()
    return {
        "attached": len(pdf_files) - len(unmatched),
        "unmatched": unmatched,
        "papers": [
            paper_map[r.paper_id].model_dump(mode="json")
            for r in rows
            if r.paper_id in paper_map
        ],
    }


@router.get("/projects/{project_id}/text-coverage")
async def text_coverage(project_id: str, db: AsyncSession = Depends(get_db)):
    from app.enrichment.paper_enricher import enrich_papers, has_analyzable_text, text_source_label

    result = await db.execute(
        select(ProjectPaper).where(ProjectPaper.project_id == project_id)
    )
    rows = result.scalars().all()
    papers = [paper_from_db(r) for r in rows]
    if not papers:
        raise HTTPException(400, "Nenhum trabalho na coleção.")

    enriched, coverage = await enrich_papers(papers)
    return {
        **coverage,
        "papers": [
            {
                "id": p.id,
                "title": p.title,
                "has_text": has_analyzable_text(p),
                "text_source": text_source_label(p),
            }
            for p in enriched
        ],
    }


@router.post(
    "/projects/{project_id}/analyze-collection",
    response_model=CollectionAnalysisResponse,
    dependencies=[Depends(require_llm)],
)
async def analyze_collection(
    project_id: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Project not found")

    result = await db.execute(
        select(ProjectPaper).where(ProjectPaper.project_id == project_id)
    )
    rows = result.scalars().all()
    papers = [paper_from_db(r) for r in rows]
    if not papers:
        raise HTTPException(400, "Importe uma coleção Mendeley antes de analisar.")

    try:
        updated, analysis = await extractor.analyze_mendeley_collection(papers)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Mendeley collection analysis failed for project %s", project_id)
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao analisar a coleção: {exc}",
        ) from exc

    paper_map = {p.id: p for p in updated}
    for row in rows:
        if row.paper_id in paper_map:
            row.paper_data = paper_to_dict(paper_map[row.paper_id])

    project.analysis_data = analysis.model_dump(mode="json")
    await db.commit()
    return analysis


@router.get("/projects/{project_id}/export")
async def export_project(project_id: str, format: str = "csv", db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ProjectPaper).where(
            ProjectPaper.project_id == project_id,
            ProjectPaper.selected == True,  # noqa: E712
        )
    )
    rows = result.scalars().all()
    papers = [paper_from_db(r) for r in rows]

    if format == "bibtex":
        return PlainTextResponse(papers_to_bibtex(papers), media_type="text/plain")
    return PlainTextResponse(papers_to_csv(papers), media_type="text/csv")


@router.post(
    "/projects/{project_id}/synthesize",
    response_model=SynthesisResponse,
    dependencies=[Depends(require_llm)],
)
async def synthesize_project(project_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ProjectPaper).where(ProjectPaper.project_id == project_id)
    )
    rows = result.scalars().all()
    papers = [paper_from_db(r) for r in rows]

    with_gaps = [p for p in papers if p.gaps]
    if not with_gaps:
        papers = await extractor.extract_batch(papers[:15], ["gaps"])

    synthesis = await extractor.synthesize_gaps(papers)
    return SynthesisResponse(**synthesis)


# ---------------------------------------------------------------------------
# PDF Batch Analysis — SSE streaming endpoint
# ---------------------------------------------------------------------------

def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/analyze-pdfs", dependencies=[Depends(require_llm)])
async def analyze_pdfs(files: list[UploadFile] = File(...)):
    """
    Recebe até 50 PDFs, extrai objetivos/metodologia/resultados/lacunas de cada
    um via LLM e analisa correlações cruzadas.
    Retorna um stream SSE com eventos de progresso e resultado final.
    """
    from app.analysis.pdf_batch import analyze_correlations, extract_single_pdf

    pdf_files: list[tuple[str, bytes]] = []
    for f in files:
        filename = f.filename or "documento.pdf"
        if not filename.lower().endswith(".pdf"):
            continue
        content = await f.read()
        pdf_files.append((filename, content))

    if not pdf_files:
        raise HTTPException(400, "Envie pelo menos um arquivo PDF.")
    if len(pdf_files) > MAX_PDF_FILES:
        raise HTTPException(400, f"Máximo de {MAX_PDF_FILES} PDFs por análise.")

    async def event_stream():
        yield _sse({"type": "start", "total": len(pdf_files)})

        extracted = []
        for i, (filename, content) in enumerate(pdf_files):
            yield _sse({
                "type": "progress",
                "index": i + 1,
                "total": len(pdf_files),
                "filename": filename,
                "stage": "extracting",
            })

            paper = await extract_single_pdf(filename, content)
            extracted.append(paper)

            yield _sse({
                "type": "paper",
                "index": i + 1,
                "paper": paper.model_dump(mode="json"),
            })

        yield _sse({
            "type": "progress",
            "index": len(pdf_files),
            "total": len(pdf_files),
            "filename": "Analisando correlações entre os trabalhos...",
            "stage": "correlating",
        })

        correlations, narrative = await analyze_correlations(extracted)

        yield _sse({
            "type": "correlations",
            "correlations": [c.model_dump(mode="json") for c in correlations],
            "narrative": narrative,
        })

        analyzed = sum(1 for p in extracted if not p.error)
        yield _sse({
            "type": "done",
            "total": len(pdf_files),
            "analyzed": analyzed,
        })

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.post(
    "/analyze-pdfs/chat",
    response_model=PdfAnalysisChatResponse,
    dependencies=[Depends(require_llm)],
)
async def chat_about_pdfs(request: PdfAnalysisChatRequest):
    """Chat contextual sobre a análise de PDFs já realizada."""
    if not request.papers:
        raise HTTPException(400, "Nenhum trabalho na análise para contextualizar o chat.")

    from app.analysis.pdf_chat import chat_about_pdf_analysis

    try:
        reply = await chat_about_pdf_analysis(
            message=request.message,
            papers=request.papers,
            correlations=request.correlations,
            narrative=request.narrative,
            history=request.history,
        )
    except Exception as exc:
        logger.exception("PDF analysis chat failed")
        raise HTTPException(500, f"Erro no chat: {exc}") from exc

    return PdfAnalysisChatResponse(reply=reply)


@router.post("/analyze-pdfs/export-pdf")
async def export_pdf_analysis(request: PdfAnalysisExportRequest):
    """Gera relatório PDF da análise de PDFs."""
    if not request.papers:
        raise HTTPException(400, "Nenhum trabalho para exportar.")

    from app.export.pdf_report import build_pdf_analysis_report

    try:
        pdf_bytes = build_pdf_analysis_report(
            request.papers,
            request.correlations,
            request.narrative,
        )
    except Exception as exc:
        logger.exception("PDF export failed")
        raise HTTPException(500, f"Erro ao gerar PDF: {exc}") from exc

    filename = "estudai-relatorio-analise.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# PDF Analysis History — persistência e retomada
# ---------------------------------------------------------------------------


@router.get("/pdf-analyses", response_model=list[PdfAnalysisSummary])
async def list_pdf_analyses(db: AsyncSession = Depends(get_db)):
    from app.analysis.pdf_storage import list_pdf_analyses as _list

    return await _list(db)


@router.post("/pdf-analyses", response_model=PdfAnalysisDetail)
async def save_pdf_analysis(data: PdfAnalysisCreate, db: AsyncSession = Depends(get_db)):
    from app.analysis.pdf_storage import create_pdf_analysis, get_pdf_analysis

    if not data.papers:
        raise HTTPException(400, "Nenhum trabalho para salvar.")
    row = await create_pdf_analysis(db, data)
    detail = await get_pdf_analysis(db, row.id)
    if not detail:
        raise HTTPException(500, "Erro ao salvar análise.")
    return detail


@router.get("/pdf-analyses/{analysis_id}", response_model=PdfAnalysisDetail)
async def get_pdf_analysis_route(analysis_id: str, db: AsyncSession = Depends(get_db)):
    from app.analysis.pdf_storage import get_pdf_analysis

    detail = await get_pdf_analysis(db, analysis_id)
    if not detail:
        raise HTTPException(404, "Análise não encontrada.")
    return detail


@router.delete("/pdf-analyses/{analysis_id}")
async def delete_pdf_analysis_route(analysis_id: str, db: AsyncSession = Depends(get_db)):
    from app.analysis.pdf_storage import delete_pdf_analysis

    if not await delete_pdf_analysis(db, analysis_id):
        raise HTTPException(404, "Análise não encontrada.")
    return {"ok": True}


@router.post("/pdf-analyses/{analysis_id}/retry-failed", dependencies=[Depends(require_llm)])
async def retry_failed_pdf_extractions(
    analysis_id: str,
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Reenvia PDFs dos trabalhos que falharam na extração, atualiza a análise salva
    e recalcula correlações com a coleção completa.
    """
    from app.analysis.pdf_batch import analyze_correlations, extract_single_pdf
    from app.analysis.pdf_retry import (
        failed_papers,
        match_upload_to_analysis_filename,
        merge_retried_papers,
    )
    from app.analysis.pdf_storage import get_pdf_analysis, update_pdf_analysis_results

    detail = await get_pdf_analysis(db, analysis_id)
    if not detail:
        raise HTTPException(404, "Análise não encontrada.")

    failed = failed_papers(detail.papers)
    if not failed:
        raise HTTPException(400, "Nenhum trabalho com erro nesta análise.")

    failed_names = [p.filename for p in failed]
    uploads: list[tuple[str, bytes, str]] = []  # upload_name, content, analysis_filename
    unmatched_uploads: list[str] = []

    for f in files:
        upload_name = f.filename or "documento.pdf"
        if not upload_name.lower().endswith(".pdf"):
            continue
        content = await f.read()
        matched = match_upload_to_analysis_filename(upload_name, failed_names)
        if matched:
            uploads.append((upload_name, content, matched))
        else:
            unmatched_uploads.append(upload_name)

    if not uploads:
        raise HTTPException(
            400,
            "Nenhum PDF corresponde aos trabalhos com erro. "
            f"Envie os arquivos com os mesmos nomes: {', '.join(failed_names[:10])}"
            + ("..." if len(failed_names) > 10 else ""),
        )

    async def event_stream():
        yield _sse({
            "type": "start",
            "failed_count": len(failed),
            "matched": len(uploads),
            "unmatched": unmatched_uploads,
            "pending_filenames": failed_names,
        })

        retried: dict[str, object] = {}
        for i, (upload_name, content, analysis_filename) in enumerate(uploads):
            yield _sse({
                "type": "progress",
                "index": i + 1,
                "total": len(uploads),
                "filename": analysis_filename,
                "stage": "extracting",
            })

            paper = await extract_single_pdf(upload_name, content)
            paper.filename = analysis_filename
            retried[analysis_filename] = paper

            yield _sse({
                "type": "paper",
                "filename": analysis_filename,
                "paper": paper.model_dump(mode="json"),
            })

        merged_papers = merge_retried_papers(detail.papers, retried)

        yield _sse({
            "type": "progress",
            "index": len(uploads),
            "total": len(uploads),
            "filename": "Recalculando correlações...",
            "stage": "correlating",
        })

        correlations, narrative = await analyze_correlations(merged_papers)

        yield _sse({
            "type": "correlations",
            "correlations": [c.model_dump(mode="json") for c in correlations],
            "narrative": narrative,
        })

        await update_pdf_analysis_results(
            db, analysis_id, merged_papers, correlations, narrative
        )
        updated = await get_pdf_analysis(db, analysis_id)

        still_failed = sum(1 for p in merged_papers if p.error)
        yield _sse({
            "type": "done",
            "analyzed": sum(1 for p in merged_papers if not p.error),
            "retried": len(uploads),
            "still_failed": still_failed,
            "analysis": updated.model_dump(mode="json") if updated else None,
        })

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.post(
    "/pdf-analyses/{analysis_id}/chat",
    response_model=PdfAnalysisChatResponse,
    dependencies=[Depends(require_llm)],
)
async def chat_pdf_analysis_persisted(
    analysis_id: str,
    request: PdfAnalysisChatPersistRequest,
    db: AsyncSession = Depends(get_db),
):
    from app.analysis.pdf_chat import chat_about_pdf_analysis
    from app.analysis.pdf_storage import append_chat_and_reply, get_pdf_analysis

    detail = await get_pdf_analysis(db, analysis_id)
    if not detail:
        raise HTTPException(404, "Análise não encontrada.")

    try:
        reply = await chat_about_pdf_analysis(
            message=request.message,
            papers=detail.papers,
            correlations=detail.correlations,
            narrative=detail.narrative,
            history=detail.messages,
        )
    except Exception as exc:
        logger.exception("PDF analysis chat failed for %s", analysis_id)
        raise HTTPException(500, f"Erro no chat: {exc}") from exc

    await append_chat_and_reply(db, analysis_id, request.message, reply)
    return PdfAnalysisChatResponse(reply=reply)
