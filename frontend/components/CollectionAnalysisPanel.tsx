"use client";

import type { CollectionAnalysis } from "@/lib/types";
import { TEXT_SOURCE_LABELS, TEXT_SOURCE_BADGE } from "@/lib/types";
import { CorrelationsPanel } from "@/components/CorrelationsPanel";
import { FileText, BarChart2 } from "lucide-react";

type Props = {
  analysis: CollectionAnalysis;
};

const SOURCE_ORDER = ["pdf_local", "pdf_open", "abstract", "crossref_abstract", "metadata_only"];

export function CollectionAnalysisPanel({ analysis }: Props) {
  const lowCoverage =
    analysis.papers_without_text > 0 && analysis.coverage_percent < 80;

  const breakdown = analysis.text_source_breakdown ?? {};
  const hasBreakdown = Object.keys(breakdown).length > 0;

  const hasCorrelations =
    (analysis.correlations?.length ?? 0) > 0 || !!analysis.narrative_summary;

  return (
    <div className="mb-4 space-y-6">
      {/* Aviso de cobertura baixa */}
      {lowCoverage && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          Apenas <strong>{analysis.papers_with_text}</strong> de{" "}
          <strong>{analysis.total_papers}</strong> trabalhos tinham texto suficiente para análise
          ({analysis.coverage_percent}%). Anexe os PDFs e reanalise para resultados mais completos.
        </div>
      )}

      {/* Breakdown de fontes textuais */}
      {hasBreakdown && (
        <div className="rounded-xl border border-gray-200 bg-white p-4">
          <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-gray-900">
            <BarChart2 className="h-4 w-4 text-brand-600" />
            Fontes de análise utilizadas
          </div>
          <div className="flex flex-wrap gap-2">
            {SOURCE_ORDER.filter((src) => breakdown[src] > 0).map((src) => (
              <span
                key={src}
                className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium ${
                  TEXT_SOURCE_BADGE[src] ?? "bg-gray-100 text-gray-600"
                }`}
              >
                <FileText className="h-3 w-3" />
                {TEXT_SOURCE_LABELS[src] ?? src}
                <span className="ml-1 rounded-full bg-white/60 px-1.5 font-semibold">
                  {breakdown[src]}
                </span>
              </span>
            ))}
          </div>
          <p className="mt-2 text-xs text-gray-500">
            {analysis.analyzed_papers} trabalho(s) com extração de conteúdo ·{" "}
            {analysis.papers_with_text} com texto disponível
          </p>
        </div>
      )}

      {/* Síntese narrativa */}
      {analysis.narrative_summary && (
        <div className="rounded-xl border border-brand-200 bg-brand-50 p-4">
          <h3 className="text-sm font-semibold text-brand-900">Síntese da coleção</h3>
          <p className="mt-2 text-sm text-brand-800 leading-relaxed">
            {analysis.narrative_summary}
          </p>
        </div>
      )}

      {/* Correlações e relações entre trabalhos */}
      {hasCorrelations && (
        <div>
          <h3 className="mb-3 text-sm font-semibold text-gray-900">
            Correlações e relações entre os trabalhos
          </h3>
          <CorrelationsPanel
            correlations={analysis.correlations ?? []}
            narrative=""
          />
        </div>
      )}

      {/* Grid de resumos */}
      <div className="grid gap-4 md:grid-cols-2">
        {analysis.shared_references.length > 0 && (
          <div className="rounded-xl border border-gray-200 bg-white p-4">
            <h3 className="text-sm font-semibold text-gray-900">
              Referências citadas em múltiplos trabalhos
            </h3>
            <ul className="mt-3 space-y-2">
              {analysis.shared_references.slice(0, 10).map((ref, i) => (
                <li key={i} className="text-xs text-gray-700">
                  <span className="font-medium">{ref.reference}</span>
                  <span className="ml-2 rounded-full bg-brand-100 px-2 py-0.5 text-brand-700">
                    {ref.count} trabalhos
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {analysis.methods_summary.length > 0 && (
          <div className="rounded-xl border border-gray-200 bg-white p-4">
            <h3 className="text-sm font-semibold text-gray-900">Métodos identificados</h3>
            <ul className="mt-3 list-disc pl-4 text-xs text-gray-700 space-y-1">
              {analysis.methods_summary.slice(0, 8).map((m, i) => (
                <li key={i}>{m}</li>
              ))}
            </ul>
          </div>
        )}

        {analysis.scopes_summary.length > 0 && (
          <div className="rounded-xl border border-gray-200 bg-white p-4">
            <h3 className="text-sm font-semibold text-gray-900">Escopos dos trabalhos</h3>
            <ul className="mt-3 list-disc pl-4 text-xs text-gray-700 space-y-1">
              {analysis.scopes_summary.slice(0, 8).map((s, i) => (
                <li key={i}>{s}</li>
              ))}
            </ul>
          </div>
        )}

        {analysis.geographic_scopes_summary.length > 0 && (
          <div className="rounded-xl border border-gray-200 bg-white p-4">
            <h3 className="text-sm font-semibold text-gray-900">Recortes geográficos</h3>
            <ul className="mt-3 list-disc pl-4 text-xs text-gray-700 space-y-1">
              {analysis.geographic_scopes_summary.slice(0, 8).map((g, i) => (
                <li key={i}>{g}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
