"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Download, FileText } from "lucide-react";
import { LlmSettingsButton } from "@/components/LlmSettingsButton";
import { LogoMark } from "@/components/Logo";
import { PdfAnalysisTable } from "@/components/PdfAnalysisTable";
import { CorrelationsPanel } from "@/components/CorrelationsPanel";
import { PdfAnalysisChat, PdfAnalysisChatFab } from "@/components/PdfAnalysisChat";
import { PdfAnalysisRetryPanel } from "@/components/PdfAnalysisRetryPanel";
import { Button } from "@/components/Button";
import { exportPdfAnalysis } from "@/lib/api";
import type { ChatMessage, CorrelationInsight, PDFPaperResult, PdfAnalysisDetail } from "@/lib/types";

type Tab = "tabela" | "correlacoes";

type Props = {
  analysisId: string;
  title: string;
  papers: PDFPaperResult[];
  correlations: CorrelationInsight[];
  narrative: string;
  messages: ChatMessage[];
  showNewAnalysisLink?: boolean;
  onAnalysisUpdated?: (analysis: PdfAnalysisDetail) => void;
};

export function PdfAnalysisWorkspace({
  analysisId,
  title,
  papers: initialPapers,
  correlations: initialCorrelations,
  narrative: initialNarrative,
  messages,
  showNewAnalysisLink = true,
  onAnalysisUpdated,
}: Props) {
  const [papers, setPapers] = useState(initialPapers);
  const [correlations, setCorrelations] = useState(initialCorrelations);
  const [narrative, setNarrative] = useState(initialNarrative);
  const [activeTab, setActiveTab] = useState<Tab>("tabela");
  const [exportingPdf, setExportingPdf] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);

  useEffect(() => {
    setPapers(initialPapers);
    setCorrelations(initialCorrelations);
    setNarrative(initialNarrative);
  }, [initialPapers, initialCorrelations, initialNarrative]);

  const failedPapers = papers.filter((p) => p.error);

  const handleRetryComplete = (analysis: PdfAnalysisDetail) => {
    setPapers(analysis.papers);
    setCorrelations(analysis.correlations);
    setNarrative(analysis.narrative);
    onAnalysisUpdated?.(analysis);
  };

  const handleExportCsv = () => {
    const headers = [
      "Arquivo",
      "Título",
      "Autores",
      "Ano",
      "Objetivos",
      "Metodologia",
      "Resultados",
      "Lacunas",
    ];
    const rows = papers.map((p) => [
      p.filename,
      p.title,
      p.authors.join("; "),
      p.year ?? "",
      p.objectives ?? "",
      p.methodology ?? "",
      p.results ?? "",
      p.gaps ?? "",
    ]);
    const csv = [headers, ...rows]
      .map((r) => r.map((v) => `"${String(v).replace(/"/g, '""')}"`).join(","))
      .join("\n");
    const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "estudai-analise-pdfs.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleExportPdf = async () => {
    setExportingPdf(true);
    try {
      const blob = await exportPdfAnalysis({ papers, correlations, narrative });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "estudai-relatorio-analise.pdf";
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Erro ao exportar PDF");
    } finally {
      setExportingPdf(false);
    }
  };

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-gray-50">
      <header className="shrink-0 border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-full items-center gap-3 px-6 py-4">
          <Link href="/analise-pdf" className="text-gray-500 hover:text-gray-700">
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <Link href="/" aria-label="Página inicial">
            <LogoMark className="h-7 w-7" />
          </Link>
          <div className="min-w-0 flex-1">
            <h1 className="truncate text-sm font-semibold text-gray-900">{title}</h1>
            <p className="text-xs text-gray-500">
              {papers.length} trabalho{papers.length !== 1 ? "s" : ""} · Análise salva
            </p>
          </div>
          <LlmSettingsButton className="shrink-0" />
          {papers.length > 0 && (
            <div className="flex shrink-0 gap-2">
              <Button
                variant="secondary"
                onClick={handleExportPdf}
                disabled={exportingPdf}
                className="gap-2"
              >
                <Download className="h-4 w-4" />
                {exportingPdf ? "Gerando PDF..." : "Exportar PDF"}
              </Button>
              <Button variant="secondary" onClick={handleExportCsv} className="gap-2">
                <Download className="h-4 w-4" />
                Exportar CSV
              </Button>
            </div>
          )}
        </div>
      </header>

      <div className="flex min-h-0 flex-1 overflow-hidden">
        <main
          className={`min-h-0 min-w-0 flex-1 overflow-y-auto px-6 py-8 ${
            chatOpen ? "" : "mx-auto max-w-6xl w-full"
          }`}
        >
          <div className="mb-6 flex flex-wrap items-center gap-4 rounded-xl border border-gray-200 bg-white p-4">
            <div className="flex items-center gap-2">
              <FileText className="h-5 w-5 text-brand-600" />
              <span className="text-sm text-gray-700">
                <strong>{papers.length}</strong> trabalho{papers.length !== 1 ? "s" : ""}
                <span className="ml-1 text-green-600">(análise completa)</span>
              </span>
            </div>
            {correlations.length > 0 && (
              <div className="text-sm text-gray-700">
                <strong>{correlations.length}</strong>{" "}
                {correlations.length !== 1 ? "correlações identificadas" : "correlação identificada"}
              </div>
            )}
            {showNewAnalysisLink && (
              <Link
                href="/analise-pdf"
                className="ml-auto text-xs text-brand-600 hover:underline"
              >
                Nova análise
              </Link>
            )}
          </div>

          {failedPapers.length > 0 && (
            <PdfAnalysisRetryPanel
              analysisId={analysisId}
              failedPapers={failedPapers}
              onComplete={handleRetryComplete}
            />
          )}

          <div className="mb-4 flex w-fit gap-1 rounded-lg border border-gray-200 bg-white p-1">
            {(["tabela", "correlacoes"] as Tab[]).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`rounded-md px-4 py-1.5 text-sm font-medium transition-colors ${
                  activeTab === tab
                    ? "bg-brand-600 text-white"
                    : "text-gray-600 hover:bg-gray-100"
                }`}
              >
                {tab === "tabela"
                  ? `Tabela (${papers.length})`
                  : `Correlações (${correlations.length})`}
              </button>
            ))}
          </div>

          {activeTab === "tabela" && <PdfAnalysisTable papers={papers} />}
          {activeTab === "correlacoes" && (
            <CorrelationsPanel correlations={correlations} narrative={narrative} />
          )}
        </main>

        {chatOpen && (
          <aside className="hidden md:flex h-full min-h-0 w-1/3 min-w-[340px] max-w-[520px] shrink-0 flex-col overflow-hidden border-l border-gray-200 bg-white">
            <PdfAnalysisChat
              key={analysisId}
              analysisId={analysisId}
              papers={papers}
              correlations={correlations}
              narrative={narrative}
              initialMessages={messages}
              onClose={() => setChatOpen(false)}
            />
          </aside>
        )}
      </div>

      {chatOpen && (
        <div className="fixed inset-0 z-50 flex flex-col overflow-hidden bg-white md:hidden">
          <PdfAnalysisChat
            key={`${analysisId}-mobile`}
            analysisId={analysisId}
            papers={papers}
            correlations={correlations}
            narrative={narrative}
            initialMessages={messages}
            onClose={() => setChatOpen(false)}
          />
        </div>
      )}

      {!chatOpen && <PdfAnalysisChatFab onClick={() => setChatOpen(true)} />}
    </div>
  );
}
