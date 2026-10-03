"""Gera relatório PDF da análise de coleção de PDFs."""

import io
from datetime import datetime, timezone

import fitz

from app.models.schemas import CORRELATION_CATEGORIES, CorrelationInsight, PDFPaperResult

FONT = "helv"
PAGE_W, PAGE_H = fitz.paper_size("a4")
MARGIN = 56
MAX_W = PAGE_W - 2 * MARGIN
LINE_H = 14


class _ReportBuilder:
    def __init__(self) -> None:
        self.doc = fitz.open()
        self.page = self.doc.new_page(width=PAGE_W, height=PAGE_H)
        self.y = MARGIN

    def _new_page(self) -> None:
        self.page = self.doc.new_page(width=PAGE_W, height=PAGE_H)
        self.y = MARGIN

    def _ensure(self, height: float) -> None:
        if self.y + height > PAGE_H - MARGIN:
            self._new_page()

    def heading(self, text: str, size: int = 13) -> None:
        self._ensure(LINE_H * 2)
        self.y += LINE_H * 0.5
        self.page.insert_text((MARGIN, self.y), text, fontname=FONT, fontsize=size)
        self.y += LINE_H * 1.6

    def subheading(self, text: str) -> None:
        self.heading(text, size=11)

    def line(self, text: str, size: int = 10, indent: float = 0) -> None:
        self._ensure(LINE_H)
        self.page.insert_text((MARGIN + indent, self.y), text, fontname=FONT, fontsize=size)
        self.y += LINE_H

    def paragraph(self, text: str, size: int = 10, indent: float = 0) -> None:
        if not text or not text.strip():
            return
        words = text.replace("\r", "").split()
        line = ""
        for word in words:
            candidate = f"{line} {word}".strip()
            width = fitz.get_text_length(candidate, fontname=FONT, fontsize=size)
            if width > MAX_W - indent and line:
                self.line(line, size=size, indent=indent)
                line = word
            else:
                line = candidate
        if line:
            self.line(line, size=size, indent=indent)
        self.y += LINE_H * 0.3

    def spacer(self, lines: float = 1) -> None:
        self.y += LINE_H * lines

    def to_bytes(self) -> bytes:
        buf = io.BytesIO()
        self.doc.save(buf, deflate=True)
        self.doc.close()
        return buf.getvalue()


def build_pdf_analysis_report(
    papers: list[PDFPaperResult],
    correlations: list[CorrelationInsight],
    narrative: str,
) -> bytes:
    b = _ReportBuilder()
    now = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")

    b.heading("EstudAI — Relatório de Análise Bibliográfica", size=16)
    b.line(f"Gerado em: {now}")
    b.line(f"Total de trabalhos: {len(papers)}")
    analyzed = sum(1 for p in papers if not p.error)
    b.line(f"Analisados com sucesso: {analyzed}")
    b.spacer()

    if narrative:
        b.heading("Síntese do estado da arte")
        b.paragraph(narrative)
        b.spacer()

    b.heading("Trabalhos analisados")
    for i, p in enumerate(papers, 1):
        b.subheading(f"{i}. {p.title}")
        if p.authors:
            b.line(f"Autores: {', '.join(p.authors[:6])}", size=9)
        if p.year:
            b.line(f"Ano: {p.year}", size=9)
        if p.filename:
            b.line(f"Arquivo: {p.filename}", size=9)
        if p.error:
            b.paragraph(f"Erro: {p.error}")
            b.spacer(0.5)
            continue
        if p.objectives:
            b.line("Objetivos:", size=9)
            b.paragraph(p.objectives, indent=12)
        if p.methodology:
            b.line("Metodologia:", size=9)
            b.paragraph(p.methodology, indent=12)
        if p.results:
            b.line("Resultados:", size=9)
            b.paragraph(p.results, indent=12)
        if p.gaps:
            b.line("Lacunas:", size=9)
            b.paragraph(p.gaps, indent=12)
        b.spacer(0.8)

    if correlations:
        b.heading("Correlações e relações entre os trabalhos")
        for c in correlations:
            label = CORRELATION_CATEGORIES.get(c.category, c.category)
            b.subheading(c.title)
            b.line(f"Categoria: {label}", size=9)
            b.paragraph(c.description)
            if c.papers:
                b.line(f"Trabalhos: {', '.join(c.papers[:6])}", size=9)
            b.spacer(0.5)

    b.spacer()
    b.line("— Relatório gerado pelo EstudAI (estudai)", size=8)

    return b.to_bytes()
