"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Microscope,
  Upload,
  FileText,
  Download,
} from "lucide-react";
import { Button } from "@/components/Button";
import { LlmSettingsButton } from "@/components/LlmSettingsButton";
import { LogoMark } from "@/components/Logo";
import { PaperTable, ALL_COLUMNS } from "@/components/PaperTable";
import { PaperDetail } from "@/components/PaperDetail";
import { CollectionAnalysisPanel } from "@/components/CollectionAnalysisPanel";
import {
  getProject,
  importMendeley,
  uploadPdfs,
  analyzeCollection,
  exportProject,
  getTextCoverage,
} from "@/lib/api";
import type { CollectionAnalysis, Paper } from "@/lib/types";

export default function RevisaoPage() {
  const params = useParams();
  const projectId = params.id as string;

  const bibRef = useRef<HTMLInputElement>(null);
  const pdfRef = useRef<HTMLInputElement>(null);

  const [papers, setPapers] = useState<Paper[]>([]);
  const [analysis, setAnalysis] = useState<CollectionAnalysis | null>(null);
  const [selectedPaper, setSelectedPaper] = useState<Paper | null>(null);
  const [analyzed, setAnalyzed] = useState(false);
  const [loading, setLoading] = useState(false);
  const [importing, setImporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [coverage, setCoverage] = useState<{
    with_text: number;
    without_text: number;
    coverage_percent: number;
  } | null>(null);

  const loadCoverage = useCallback(async () => {
    try {
      const c = await getTextCoverage(projectId);
      setCoverage({
        with_text: c.with_text,
        without_text: c.without_text,
        coverage_percent: c.coverage_percent,
      });
    } catch {
      setCoverage(null);
    }
  }, [projectId]);

  const load = useCallback(async () => {
    const data = await getProject(projectId);
    setPapers(data.papers);
    if (data.analysis) {
      setAnalysis(data.analysis);
      setAnalyzed(true);
    }
    await loadCoverage();
  }, [projectId, loadCoverage]);

  useEffect(() => {
    load().catch(() => setError("Não foi possível carregar a revisão."));
  }, [load]);

  const handleImportMore = async (file: File) => {
    setImporting(true);
    setError(null);
    try {
      const res = await importMendeley(projectId, file);
      setPapers(res.papers);
      setAnalyzed(false);
      setAnalysis(null);
      setStatus(res.message);
      await loadCoverage();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro na importação");
    } finally {
      setImporting(false);
    }
  };

  const handlePdfUpload = async (files: File[]) => {
    setImporting(true);
    try {
      const res = await uploadPdfs(projectId, files);
      setPapers(res.papers);
      setStatus(
        `${res.attached} PDF(s) vinculado(s) aos trabalhos.` +
          (res.unmatched.length ? ` Sem correspondência: ${res.unmatched.join(", ")}` : "")
      );
      await loadCoverage();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao anexar PDFs");
    } finally {
      setImporting(false);
    }
  };

  const handleAnalyze = async () => {
    setLoading(true);
    setError(null);
    setStatus("Analisando coleção... isso pode levar alguns minutos.");
    try {
      const result = await analyzeCollection(projectId);
      setAnalysis(result);
      setAnalyzed(true);
      await load();
      setStatus(`Análise concluída em ${result.analyzed_papers} trabalho(s).`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro na análise");
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async () => {
    const content = await exportProject(projectId, "csv");
    const blob = new Blob([content], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "estudai-revisao.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="border-b border-gray-200 bg-white px-6 py-4">
        <div className="mx-auto flex max-w-6xl items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/revisao" className="text-gray-500 hover:text-gray-700">
              <ArrowLeft className="h-5 w-5" />
            </Link>
            <Link href="/" aria-label="Página inicial">
              <LogoMark className="h-7 w-7" />
            </Link>
            <div>
              <h1 className="text-sm font-semibold text-gray-900">Revisão Mendeley</h1>
              <p className="text-xs text-gray-500">{papers.length} trabalhos na coleção</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <LlmSettingsButton />
            {analyzed && (
              <Button variant="secondary" onClick={handleExport} className="gap-2">
                <Download className="h-4 w-4" />
                Exportar CSV
              </Button>
            )}
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-8">
        {error && <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
        {status && <div className="mb-4 rounded-lg bg-blue-50 px-4 py-3 text-sm text-blue-800">{status}</div>}

        {coverage && !analyzed && (
          <div
            className={`mb-4 rounded-lg border p-4 text-sm ${
              coverage.coverage_percent >= 70
                ? "border-green-200 bg-green-50 text-green-900"
                : "border-amber-200 bg-amber-50 text-amber-900"
            }`}
          >
            <strong>Cobertura de texto:</strong> {coverage.with_text} de {papers.length} trabalhos
            têm texto analisável ({coverage.coverage_percent}%).
            {coverage.without_text > 0 && (
              <>
                {" "}
                Para os demais, anexe os PDFs exportados do Mendeley — o RIS sozinho não contém o
                corpo do artigo.
              </>
            )}
          </div>
        )}

        {/* Passo 1: Importar */}
        <section className="rounded-xl border border-gray-200 bg-white p-6">
          <h2 className="text-sm font-semibold text-gray-900">1. Trabalhos da coleção</h2>
          <p className="mt-1 text-xs text-gray-500">
            O arquivo RIS traz metadados. Para analisar métodos e resultados do texto completo,
            exporte os PDFs do Mendeley e anexe abaixo.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <input
              ref={bibRef}
              type="file"
              accept=".ris,.bib,.bibtex"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) handleImportMore(f);
                if (bibRef.current) bibRef.current.value = "";
              }}
            />
            <input
              ref={pdfRef}
              type="file"
              accept=".pdf"
              multiple
              className="hidden"
              onChange={(e) => {
                const files = Array.from(e.target.files || []);
                if (files.length) handlePdfUpload(files);
                if (pdfRef.current) pdfRef.current.value = "";
              }}
            />
            <Button variant="secondary" disabled={importing} onClick={() => bibRef.current?.click()} className="gap-2">
              <Upload className="h-4 w-4" />
              Adicionar do Mendeley
            </Button>
            <Button variant="secondary" disabled={importing} onClick={() => pdfRef.current?.click()} className="gap-2">
              <FileText className="h-4 w-4" />
              Anexar PDFs (recomendado)
            </Button>
          </div>

          <div className="mt-6">
            <PaperTable
              papers={papers}
              visibleColumns={analyzed ? ALL_COLUMNS : []}
              onSelectPaper={setSelectedPaper}
              selectedPaperId={selectedPaper?.id}
            />
          </div>
        </section>

        {/* Passo 2: Analisar */}
        {!analyzed && (
          <section className="mt-6 rounded-xl border border-brand-200 bg-brand-50 p-8 text-center">
            <h2 className="text-lg font-semibold text-brand-900">2. Analisar coleção</h2>
            <p className="mt-2 text-sm text-brand-800">
              A IA extrai lacunas, métodos, escopo e referências a partir do resumo (quando
              disponível via DOI) ou do PDF anexado. Sem texto, a análise fica limitada aos
              metadados.
            </p>
            <Button
              className="mt-6 px-8 py-3 text-base"
              onClick={handleAnalyze}
              disabled={loading || papers.length === 0}
            >
              <Microscope className="mr-2 h-5 w-5" />
              {loading ? "Analisando..." : "Analisar coleção"}
            </Button>
          </section>
        )}

        {/* Passo 3: Resultados */}
        {analyzed && analysis && (
          <section className="mt-6">
            <h2 className="mb-4 text-sm font-semibold text-gray-900">3. Resultados da análise</h2>
            <CollectionAnalysisPanel analysis={analysis} />
            <div className="mt-6">
              <PaperTable
                papers={papers}
                visibleColumns={ALL_COLUMNS}
                onSelectPaper={setSelectedPaper}
                selectedPaperId={selectedPaper?.id}
              />
            </div>
            <div className="mt-6 text-center">
              <Button variant="secondary" onClick={handleAnalyze} disabled={loading}>
                {loading ? "Reanalisando..." : "Reanalisar coleção"}
              </Button>
            </div>
          </section>
        )}
      </main>

      {selectedPaper && (
        <PaperDetail paper={selectedPaper} onClose={() => setSelectedPaper(null)} />
      )}
    </div>
  );
}
