"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Loader2 } from "lucide-react";
import { PdfAnalysisWorkspace } from "@/components/PdfAnalysisWorkspace";
import { getPdfAnalysis } from "@/lib/api";
import type { PdfAnalysisDetail } from "@/lib/types";

export default function PdfAnalysisDetailPage() {
  const params = useParams();
  const analysisId = params.id as string;
  const [analysis, setAnalysis] = useState<PdfAnalysisDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await getPdfAnalysis(analysisId);
        if (!cancelled) setAnalysis(data);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Erro ao carregar análise");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    if (analysisId) load();
    return () => {
      cancelled = true;
    };
  }, [analysisId]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50">
        <div className="flex items-center gap-3 text-gray-600">
          <Loader2 className="h-6 w-6 animate-spin text-brand-600" />
          <span>Carregando análise...</span>
        </div>
      </div>
    );
  }

  if (error || !analysis) {
    return (
      <div className="flex min-h-screen flex-col bg-gray-50">
        <header className="border-b border-gray-200 bg-white px-6 py-4">
          <Link href="/analise-pdf" className="inline-flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900">
            <ArrowLeft className="h-4 w-4" />
            Voltar
          </Link>
        </header>
        <div className="mx-auto mt-16 max-w-md rounded-xl border border-red-200 bg-red-50 p-6 text-center">
          <p className="text-sm text-red-700">{error ?? "Análise não encontrada."}</p>
          <Link href="/analise-pdf" className="mt-4 inline-block text-sm text-brand-600 hover:underline">
            Fazer nova análise
          </Link>
        </div>
      </div>
    );
  }

  return (
    <PdfAnalysisWorkspace
      analysisId={analysis.id}
      title={analysis.title}
      papers={analysis.papers}
      correlations={analysis.correlations}
      narrative={analysis.narrative}
      messages={analysis.messages}
      onAnalysisUpdated={setAnalysis}
    />
  );
}
