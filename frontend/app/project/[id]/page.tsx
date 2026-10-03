"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Download, Plus, Sparkles } from "lucide-react";
import { ChatPanel } from "@/components/ChatPanel";
import { LlmSettingsButton } from "@/components/LlmSettingsButton";
import { LogoMark } from "@/components/Logo";
import { PaperTable, ALL_COLUMNS, COLUMN_LABELS, type ColumnKey } from "@/components/PaperTable";
import { PaperDetail } from "@/components/PaperDetail";
import { ImportDialog } from "@/components/ImportDialog";
import { Button } from "@/components/Button";
import {
  getProject,
  sendChat,
  importReferences,
  exportProject,
  synthesizeGaps,
} from "@/lib/api";
import type { ChatMessage, Paper, Synthesis } from "@/lib/types";

const SEARCH_COLUMNS: ColumnKey[] = ["objectives", "results", "gaps"];

export default function ProjectPage() {
  const params = useParams();
  const projectId = params.id as string;

  const [title, setTitle] = useState("");
  const [papers, setPapers] = useState<Paper[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [visibleColumns, setVisibleColumns] = useState<ColumnKey[]>([]);
  const [selectedPaper, setSelectedPaper] = useState<Paper | null>(null);
  const [loading, setLoading] = useState(false);
  const [importing, setImporting] = useState(false);
  const [synthesis, setSynthesis] = useState<Synthesis | null>(null);
  const [showExport, setShowExport] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadProject = useCallback(async () => {
    try {
      const data = await getProject(projectId);
      setTitle(data.title);
      setPapers(data.papers);
      setMessages(data.messages);
    } catch {
      setError("Projeto não encontrado ou backend indisponível.");
    }
  }, [projectId]);

  useEffect(() => {
    loadProject();
  }, [loadProject]);

  const handleSend = async (message: string) => {
    setLoading(true);
    setError(null);
    setMessages((prev) => [...prev, { role: "user", content: message }]);

    try {
      const res = await sendChat(message, projectId);
      setMessages((prev) => [...prev, { role: "assistant", content: res.reply }]);
      if (res.papers.length > 0) setPapers(res.papers);
      if (res.action === "extract") setVisibleColumns(SEARCH_COLUMNS);
      if (res.action === "synthesize") setSynthesis(await synthesizeGaps(projectId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao processar mensagem");
    } finally {
      setLoading(false);
    }
  };

  const handleImport = async (file: File) => {
    setImporting(true);
    try {
      const res = await importReferences(projectId, file);
      setPapers((prev) => [...prev, ...res.papers]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro na importação");
    } finally {
      setImporting(false);
    }
  };

  const handleExport = async (format: "csv" | "bibtex") => {
    const content = await exportProject(projectId, format);
    const blob = new Blob([content], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `estudai-export.${format === "bibtex" ? "bib" : "csv"}`;
    a.click();
    URL.revokeObjectURL(url);
    setShowExport(false);
  };

  const handleSynthesize = async () => {
    setLoading(true);
    try {
      setSynthesis(await synthesizeGaps(projectId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro na síntese");
    } finally {
      setLoading(false);
    }
  };

  const toggleColumn = (col: ColumnKey) => {
    setVisibleColumns((prev) =>
      prev.includes(col) ? prev.filter((c) => c !== col) : [...prev, col]
    );
  };

  return (
    <div className="flex h-screen flex-col bg-gray-100">
      <header className="flex items-center justify-between border-b border-gray-200 bg-white px-4 py-3">
        <div className="flex items-center gap-3">
          <Link href="/" className="text-gray-500 hover:text-gray-700">
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <Link href="/" aria-label="Página inicial">
            <LogoMark className="h-7 w-7" />
          </Link>
          <div>
            <h1 className="text-sm font-semibold text-gray-900 line-clamp-1 max-w-md">
              {title || "Busca bibliográfica"}
            </h1>
            <p className="text-xs text-gray-500">{papers.length} trabalhos</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <LlmSettingsButton />
          <Button variant="secondary" onClick={handleSynthesize} disabled={loading || papers.length === 0}>
            <Sparkles className="mr-1 h-4 w-4" />
            Mapa de lacunas
          </Button>
          <div className="relative">
            <Button variant="secondary" onClick={() => setShowExport(!showExport)}>
              <Download className="mr-1 h-4 w-4" />
              Exportar
            </Button>
            {showExport && (
              <div className="absolute right-0 z-10 mt-1 w-40 rounded-lg border border-gray-200 bg-white py-1 shadow-lg">
                <button className="block w-full px-4 py-2 text-left text-sm hover:bg-gray-50" onClick={() => handleExport("csv")}>
                  CSV
                </button>
                <button className="block w-full px-4 py-2 text-left text-sm hover:bg-gray-50" onClick={() => handleExport("bibtex")}>
                  BibTeX
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      {error && <div className="bg-red-50 px-4 py-2 text-sm text-red-700">{error}</div>}

      <div className="flex flex-1 overflow-hidden">
        <div className="w-80 shrink-0">
          <ChatPanel messages={messages} onSend={handleSend} loading={loading} />
        </div>

        <div className="flex flex-1 flex-col overflow-hidden p-4">
          <div className="mb-4 flex flex-wrap items-center gap-2">
            <ImportDialog onImport={handleImport} loading={importing} />
            <div className="flex items-center gap-1 text-xs text-gray-500">
              <Plus className="h-3 w-3" />
              Colunas:
            </div>
            {SEARCH_COLUMNS.map((col) => (
              <button
                key={col}
                onClick={() => toggleColumn(col)}
                className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                  visibleColumns.includes(col)
                    ? "bg-brand-600 text-white"
                    : "bg-gray-200 text-gray-600 hover:bg-gray-300"
                }`}
              >
                {COLUMN_LABELS[col]}
              </button>
            ))}
          </div>

          {synthesis && (
            <div className="mb-4 rounded-xl border border-brand-200 bg-brand-50 p-4">
              <h3 className="text-sm font-semibold text-brand-900">Mapa de lacunas</h3>
              <p className="mt-2 text-sm text-brand-800">{synthesis.summary}</p>
            </div>
          )}

          <div className="flex-1 overflow-y-auto">
            <PaperTable
              papers={papers}
              visibleColumns={visibleColumns}
              onSelectPaper={setSelectedPaper}
              selectedPaperId={selectedPaper?.id}
            />
          </div>
        </div>
      </div>

      {selectedPaper && (
        <PaperDetail paper={selectedPaper} onClose={() => setSelectedPaper(null)} />
      )}
    </div>
  );
}
