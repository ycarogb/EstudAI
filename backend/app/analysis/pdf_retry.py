"""Reextração de trabalhos com erro em análises PDF salvas."""

from __future__ import annotations

from app.models.schemas import PDFPaperResult


def normalize_filename(name: str) -> str:
    return name.lower().strip().replace("\\", "/").split("/")[-1]


def failed_papers(papers: list[PDFPaperResult]) -> list[PDFPaperResult]:
    return [p for p in papers if p.error]


def match_upload_to_analysis_filename(
    upload_name: str,
    failed_filenames: list[str],
) -> str | None:
    """Associa PDF enviado ao filename original da análise (case-insensitive)."""
    norm_upload = normalize_filename(upload_name)
    for original in failed_filenames:
        if normalize_filename(original) == norm_upload:
            return original
    return None


def merge_retried_papers(
    existing: list[PDFPaperResult],
    retried_by_filename: dict[str, PDFPaperResult],
) -> list[PDFPaperResult]:
    merged: list[PDFPaperResult] = []
    for paper in existing:
        replacement = retried_by_filename.get(paper.filename)
        merged.append(replacement if replacement else paper)
    return merged


def count_analyzed(papers: list[PDFPaperResult]) -> int:
    return sum(1 for p in papers if not p.error)
