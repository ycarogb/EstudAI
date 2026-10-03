"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  Clock,
  FileText,
  Loader2,
  Trash2,
} from "lucide-react";
import { PdfDropzone } from "@/components/PdfDropzone";
import { Button } from "@/components/Button";
import { LlmSettingsButton } from "@/components/LlmSettingsButton";
import { LogoMark } from "@/components/Logo";
import { analyzePdfs, deletePdfAnalysis, listPdfAnalyses, savePdfAnalysis } from "@/lib/api";
import type { CorrelationInsight, PDFAnalysisState, PDFPaperResult, PdfAnalysisSummary } from "@/lib/types";

const INITIAL_STATE: PDFAnalysisState = {
  status: "idle",
  total: 0,
  current: 0,
  currentFilename: "",
  papers: [],
  correlations: [],
  narrative: "",
  analyzed: 0,
};

function formatDate(iso: string) {
  return new Date(iso).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function AnalisePdfPage() {
  const router = useRouter();
  const [state, setState] = useState<PDFAnalysisState>(INITIAL_STATE);
  const [history, setHistory] = useState<PdfAnalysisSummary[]>([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const loadHistory = useCallback(async () => {
    setHistoryLoading(true);
    try {
      const items = await listPdfAnalyses();
      setHistory(items);
    } catch {
      setHistory([]);
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  const handleAnalyze = useCallback(
    async (files: File[]) => {
      abortRef.current = new AbortController();
      setState({
        ...INITIAL_STATE,
        status: "uploading",
        total: files.length,
      });

      let papers: PDFPaperResult[] = [];
      let correlations: CorrelationInsight[] = [];
      let narrative = "";
      let analyzed = 0;

      try {
        await analyzePdfs(
          files,
          (event) => {
            if (event.type === "start") {
              setState((s) => ({ ...s, status: "processing", total: event.total }));
            } else if (event.type === "progress") {
              setState((s) => ({
                ...s,
                status: event.stage === "correlating" ? "correlating" : "processing",
                current: event.index,
                currentFilename: event.filename,
              }));
            } else if (event.type === "paper") {
              papers = [...papers, event.paper];
              setState((s) => ({
                ...s,
                papers,
              }));
            } else if (event.type === "correlations") {
              correlations = event.correlations;
              narrative = event.narrative;
              setState((s) => ({
                ...s,
                correlations,
                narrative,
              }));
            } else if (event.type === "done") {
              analyzed = event.analyzed;
              setState((s) => ({
                ...s,
                status: "done",
                analyzed: event.analyzed,
              }));
            }
          },
          abortRef.current.signal
        );

        if (papers.length === 0) {
          setState((s) => ({
            ...s,
            status: "error",
            errorMessage: "Nenhum trabalho foi extraído dos PDFs enviados.",
          }));
          return;
        }

        setSaving(true);
        const saved = await savePdfAnalysis({
          papers,
          correlations,
          narrative,
          analyzed,
          total: files.length,
        });
        router.push(`/analise-pdf/${saved.id}`);
      } catch (err) {
        if ((err as Error).name === "AbortError") return;
        setState((s) => ({
          ...s,
          status: "error",
          errorMessage: err instanceof Error ? err.message : "Erro desconhecido",
        }));
      } finally {
        setSaving(false);
      }
    },
    [router]
  );

  const handleCancel = () => {
    abortRef.current?.abort();
    setState(INITIAL_STATE);
  };

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!confirm("Excluir esta análise do histórico?")) return;
    try {
      await deletePdfAnalysis(id);
      setHistory((items) => items.filter((item) => item.id !== id));
    } catch (err) {
      alert(err instanceof Error ? err.message : "Erro ao excluir");
    }
  };

  const isRunning =
    state.status === "uploading" ||
    state.status === "processing" ||
    state.status === "correlating" ||
    saving;

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-4xl items-center gap-3 px-6 py-4">
          <Link href="/" className="text-gray-500 hover:text-gray-700">
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <Link href="/" aria-label="Página inicial">
            <LogoMark className="h-7 w-7" />
          </Link>
          <div className="flex-1">
            <h1 className="text-sm font-semibold text-gray-900">Análise de PDFs</h1>
            <p className="text-xs text-gray-500">
              Até 50 PDFs · Análises salvas automaticamente no histórico
            </p>
          </div>
          <LlmSettingsButton />
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-6 py-8">
        {!isRunning && (
          <>
            <div className="mb-6 rounded-lg border border-blue-200 bg-blue-50 p-4 text-sm text-blue-900">
              <strong>Como funciona:</strong> Faça upload dos PDFs. Ao concluir, a análise é salva
              automaticamente e você pode retomar depois — incluindo a conversa com o assistente —
              sem precisar reenviar os arquivos.
            </div>

            <PdfDropzone onAnalyze={handleAnalyze} disabled={isRunning} />

            {state.status === "error" && (
              <div className="mt-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
                {state.errorMessage}
              </div>
            )}

            <section className="mt-10">
              <div className="mb-4 flex items-center justify-between">
                <h2 className="text-sm font-semibold text-gray-900">Histórico de análises</h2>
                {!historyLoading && history.length > 0 && (
                  <span className="text-xs text-gray-500">{history.length} salva(s)</span>
                )}
              </div>

              {historyLoading ? (
                <div className="flex items-center gap-2 rounded-xl border border-gray-200 bg-white p-6 text-sm text-gray-500">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Carregando histórico...
                </div>
              ) : history.length === 0 ? (
                <div className="rounded-xl border border-dashed border-gray-300 bg-white p-8 text-center text-sm text-gray-500">
                  Nenhuma análise salva ainda. Faça o upload dos PDFs para começar.
                </div>
              ) : (
                <ul className="space-y-2">
                  {history.map((item) => (
                    <li key={item.id}>
                      <Link
                        href={`/analise-pdf/${item.id}`}
                        className="group flex items-center gap-4 rounded-xl border border-gray-200 bg-white p-4 transition-colors hover:border-brand-300 hover:bg-brand-50/30"
                      >
                        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-brand-100 text-brand-700">
                          <FileText className="h-5 w-5" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-medium text-gray-900 group-hover:text-brand-800">
                            {item.title}
                          </p>
                          <p className="mt-0.5 flex items-center gap-1 text-xs text-gray-500">
                            <Clock className="h-3 w-3" />
                            {formatDate(item.updated_at)} · {item.paper_count} trabalho
                            {item.paper_count !== 1 ? "s" : ""}
                          </p>
                        </div>
                        <button
                          type="button"
                          onClick={(e) => handleDelete(item.id, e)}
                          className="shrink-0 rounded-lg p-2 text-gray-400 opacity-0 transition-opacity hover:bg-red-50 hover:text-red-600 group-hover:opacity-100"
                          aria-label="Excluir análise"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </>
        )}

        {isRunning && (
          <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Loader2 className="h-5 w-5 animate-spin text-brand-600" />
                <div>
                  <p className="text-sm font-medium text-gray-900">
                    {saving
                      ? "Salvando análise no histórico..."
                      : state.status === "correlating"
                        ? "Analisando correlações entre os trabalhos..."
                        : `Processando ${state.currentFilename}`}
                  </p>
                  <p className="text-xs text-gray-500">
                    {saving
                      ? "Quase pronto — você será redirecionado em instantes"
                      : `${state.current} de ${state.total} arquivo${state.total !== 1 ? "s" : ""}`}
                  </p>
                </div>
              </div>
              {!saving && (
                <Button variant="ghost" onClick={handleCancel} className="text-xs text-gray-500">
                  Cancelar
                </Button>
              )}
            </div>

            {!saving && (
              <>
                <div className="mt-4 h-2 overflow-hidden rounded-full bg-gray-100">
                  <div
                    className="h-full rounded-full bg-brand-600 transition-all duration-500"
                    style={{
                      width: `${state.total > 0 ? (state.current / state.total) * 100 : 5}%`,
                    }}
                  />
                </div>

                {state.papers.length > 0 && (
                  <p className="mt-3 text-xs text-gray-500">
                    {state.papers.length} trabalho{state.papers.length !== 1 ? "s" : ""} extraído
                    {state.papers.length !== 1 ? "s" : ""} até agora
                  </p>
                )}
              </>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
