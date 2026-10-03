"use client";

import { useRef, useState } from "react";
import { AlertCircle, Loader2, RefreshCw, Upload } from "lucide-react";
import { retryFailedPdfAnalysis } from "@/lib/api";
import type { PDFPaperResult, PdfAnalysisDetail } from "@/lib/types";
import { Button } from "./Button";

type Props = {
  analysisId: string;
  failedPapers: PDFPaperResult[];
  onComplete: (analysis: PdfAnalysisDetail) => void;
};

function normalizeFilename(name: string) {
  return name.toLowerCase().split(/[/\\]/).pop() ?? name;
}

export function PdfAnalysisRetryPanel({ analysisId, failedPapers, onComplete }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState("");
  const [error, setError] = useState<string | null>(null);

  const failedNames = new Set(failedPapers.map((p) => normalizeFilename(p.filename)));

  const matchedCount = files.filter((f) => failedNames.has(normalizeFilename(f.name))).length;
  const unmatchedFiles = files.filter((f) => !failedNames.has(normalizeFilename(f.name)));

  const handleFiles = (list: FileList | null) => {
    if (!list) return;
    const pdfs = Array.from(list).filter((f) => f.name.toLowerCase().endsWith(".pdf"));
    setFiles(pdfs);
    setError(null);
  };

  const handleRetry = async () => {
    const toSend = files.filter((f) => failedNames.has(normalizeFilename(f.name)));
    if (toSend.length === 0) {
      setError("Selecione os PDFs com o mesmo nome dos trabalhos que falharam.");
      return;
    }

    setRunning(true);
    setError(null);
    setProgress("Iniciando reextração...");

    try {
      await retryFailedPdfAnalysis(analysisId, toSend, (event) => {
        if (event.type === "start") {
          setProgress(`${event.matched} arquivo(s) reconhecido(s) de ${event.failed_count} com erro`);
        } else if (event.type === "progress") {
          setProgress(
            event.stage === "correlating"
              ? "Recalculando correlações entre os trabalhos..."
              : `Reextraindo ${event.filename} (${event.index}/${event.total})`
          );
        } else if (event.type === "done" && event.analysis) {
          setProgress("");
          setFiles([]);
          onComplete(event.analysis);
        } else if (event.type === "error") {
          setError(event.message);
        }
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao reextrair trabalhos");
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="mb-6 rounded-xl border border-amber-200 bg-amber-50 p-5">
      <div className="flex items-start gap-3">
        <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-amber-600" />
        <div className="min-w-0 flex-1">
          <h3 className="text-sm font-semibold text-amber-900">
            {failedPapers.length} trabalho{failedPapers.length !== 1 ? "s" : ""} com erro na extração
          </h3>
          <p className="mt-1 text-sm text-amber-800">
            Reenvie os PDFs que falharam (mesmos nomes de arquivo). A extração será refeita e as
            correlações recalculadas com a coleção atualizada.
          </p>

          <ul className="mt-3 space-y-1 text-xs text-amber-900/90">
            {failedPapers.map((p) => (
              <li key={p.filename} className="truncate font-mono">
                {p.filename}
                {p.error && (
                  <span className="ml-2 font-sans text-amber-700">— {p.error}</span>
                )}
              </li>
            ))}
          </ul>

          <div className="mt-4 flex flex-wrap items-center gap-3">
            <input
              ref={inputRef}
              type="file"
              accept=".pdf,application/pdf"
              multiple
              className="hidden"
              onChange={(e) => handleFiles(e.target.files)}
            />
            <Button
              type="button"
              variant="secondary"
              className="gap-2"
              disabled={running}
              onClick={() => inputRef.current?.click()}
            >
              <Upload className="h-4 w-4" />
              Selecionar PDFs
            </Button>
            <Button
              type="button"
              className="gap-2"
              disabled={running || matchedCount === 0}
              onClick={handleRetry}
            >
              {running ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4" />
              )}
              {running ? "Processando..." : "Reextrair e atualizar correlações"}
            </Button>
          </div>

          {files.length > 0 && (
            <p className="mt-2 text-xs text-amber-800">
              {matchedCount} de {files.length} arquivo(s) correspondem a trabalhos com erro.
            </p>
          )}

          {unmatchedFiles.length > 0 && (
            <p className="mt-1 text-xs text-amber-700">
              Ignorados (nome não bate com erro):{" "}
              {unmatchedFiles.map((f) => f.name).join(", ")}
            </p>
          )}

          {progress && (
            <p className="mt-2 flex items-center gap-2 text-sm text-amber-900">
              <Loader2 className="h-4 w-4 animate-spin" />
              {progress}
            </p>
          )}

          {error && (
            <p className="mt-2 rounded-lg bg-red-100 px-3 py-2 text-sm text-red-700">{error}</p>
          )}
        </div>
      </div>
    </div>
  );
}
