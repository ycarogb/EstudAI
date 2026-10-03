"""Persistência de sessões de análise de PDFs."""

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import PdfAnalysis, PdfAnalysisMessage
from app.models.schemas import (
    CorrelationInsight,
    PDFPaperResult,
    PdfAnalysisChatMessage,
    PdfAnalysisCreate,
    PdfAnalysisDetail,
    PdfAnalysisSummary,
)


def _default_title(papers: list[PDFPaperResult]) -> str:
    if not papers:
        return "Análise de PDFs"
    first = papers[0].title or papers[0].filename
    if len(papers) == 1:
        return first[:120]
    return f"{first[:80]} (+{len(papers) - 1} trabalhos)"


async def create_pdf_analysis(db: AsyncSession, data: PdfAnalysisCreate) -> PdfAnalysis:
    title = data.title or _default_title(data.papers)
    row = PdfAnalysis(
        title=title,
        papers_data=[p.model_dump(mode="json") for p in data.papers],
        correlations_data=[c.model_dump(mode="json") for c in data.correlations],
        narrative=data.narrative,
        analyzed=data.analyzed,
        total=data.total or len(data.papers),
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def list_pdf_analyses(db: AsyncSession) -> list[PdfAnalysisSummary]:
    result = await db.execute(
        select(PdfAnalysis).order_by(PdfAnalysis.updated_at.desc())
    )
    rows = result.scalars().all()
    return [
        PdfAnalysisSummary(
            id=r.id,
            title=r.title,
            created_at=r.created_at.isoformat(),
            updated_at=r.updated_at.isoformat(),
            total=r.total,
            analyzed=r.analyzed,
            paper_count=len(r.papers_data or []),
        )
        for r in rows
    ]


async def get_pdf_analysis(db: AsyncSession, analysis_id: str) -> PdfAnalysisDetail | None:
    result = await db.execute(
        select(PdfAnalysis)
        .where(PdfAnalysis.id == analysis_id)
        .options(selectinload(PdfAnalysis.messages))
    )
    row = result.scalar_one_or_none()
    if not row:
        return None

    papers = [PDFPaperResult(**p) for p in (row.papers_data or [])]
    correlations = [CorrelationInsight(**c) for c in (row.correlations_data or [])]
    messages = [
        PdfAnalysisChatMessage(role=m.role, content=m.content)
        for m in row.messages
    ]

    return PdfAnalysisDetail(
        id=row.id,
        title=row.title,
        created_at=row.created_at.isoformat(),
        updated_at=row.updated_at.isoformat(),
        papers=papers,
        correlations=correlations,
        narrative=row.narrative or "",
        analyzed=row.analyzed,
        total=row.total,
        messages=messages,
    )


async def delete_pdf_analysis(db: AsyncSession, analysis_id: str) -> bool:
    result = await db.execute(select(PdfAnalysis).where(PdfAnalysis.id == analysis_id))
    row = result.scalar_one_or_none()
    if not row:
        return False
    await db.delete(row)
    await db.commit()
    return True


async def update_pdf_analysis_results(
    db: AsyncSession,
    analysis_id: str,
    papers: list[PDFPaperResult],
    correlations: list[CorrelationInsight],
    narrative: str,
) -> PdfAnalysis | None:
    result = await db.execute(select(PdfAnalysis).where(PdfAnalysis.id == analysis_id))
    row = result.scalar_one_or_none()
    if not row:
        return None

    row.papers_data = [p.model_dump(mode="json") for p in papers]
    row.correlations_data = [c.model_dump(mode="json") for c in correlations]
    row.narrative = narrative
    row.analyzed = sum(1 for p in papers if not p.error)
    row.total = len(papers)
    await db.commit()
    await db.refresh(row)
    return row


async def append_chat_and_reply(
    db: AsyncSession,
    analysis_id: str,
    user_message: str,
    assistant_reply: str,
) -> None:
    db.add(PdfAnalysisMessage(analysis_id=analysis_id, role="user", content=user_message))
    db.add(PdfAnalysisMessage(analysis_id=analysis_id, role="assistant", content=assistant_reply))
    await db.execute(
        update(PdfAnalysis).where(PdfAnalysis.id == analysis_id).values(updated_at=func.now())
    )
    await db.commit()
