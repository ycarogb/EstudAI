"use client";

import type { Paper } from "@/lib/types";
import { getSourceLabel } from "@/lib/api";
import { X, ExternalLink } from "lucide-react";

type Props = {
  paper: Paper;
  onClose: () => void;
};

export function PaperDetail({ paper, onClose }: Props) {
  return (
    <div className="fixed inset-y-0 right-0 z-50 w-full max-w-lg overflow-y-auto border-l border-gray-200 bg-white shadow-xl">
      <div className="sticky top-0 flex items-center justify-between border-b border-gray-200 bg-white px-6 py-4">
        <h3 className="text-sm font-semibold text-gray-900">Detalhe do trabalho</h3>
        <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
          <X className="h-5 w-5" />
        </button>
      </div>

      <div className="space-y-6 p-6">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">{paper.title}</h2>
          <p className="mt-2 text-sm text-gray-600">{paper.authors.join(", ")}</p>
          <div className="mt-2 flex flex-wrap gap-2 text-xs">
            {paper.year && (
              <span className="rounded bg-gray-100 px-2 py-1">{paper.year}</span>
            )}
            <span className="rounded bg-gray-100 px-2 py-1">{getSourceLabel(paper.source)}</span>
            {paper.document_type && (
              <span className="rounded bg-gray-100 px-2 py-1">{paper.document_type}</span>
            )}
          </div>
        </div>

        {paper.url && (
          <a
            href={paper.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-sm text-brand-600 hover:underline"
          >
            Abrir fonte original <ExternalLink className="h-3 w-3" />
          </a>
        )}

        {paper.abstract && (
          <section>
            <h4 className="text-sm font-medium text-gray-900">Resumo</h4>
            <p className="mt-2 text-sm text-gray-700 leading-relaxed">{paper.abstract}</p>
          </section>
        )}

        {paper.objectives && (
          <section>
            <h4 className="text-sm font-medium text-gray-900">Objetivos</h4>
            <p className="mt-2 text-sm text-gray-700">{paper.objectives}</p>
          </section>
        )}

        {paper.results && (
          <section>
            <h4 className="text-sm font-medium text-gray-900">Resultados</h4>
            <p className="mt-2 text-sm text-gray-700">{paper.results}</p>
          </section>
        )}

        {paper.gaps && (
          <section>
            <h4 className="text-sm font-medium text-gray-900">Lacunas</h4>
            <p className="mt-2 text-sm text-gray-700">{paper.gaps}</p>
          </section>
        )}

        {paper.methods && (
          <section>
            <h4 className="text-sm font-medium text-gray-900">Métodos</h4>
            <p className="mt-2 text-sm text-gray-700">{paper.methods}</p>
          </section>
        )}

        {paper.scope && (
          <section>
            <h4 className="text-sm font-medium text-gray-900">Escopo</h4>
            <p className="mt-2 text-sm text-gray-700">{paper.scope}</p>
          </section>
        )}

        {paper.geographic_scope && (
          <section>
            <h4 className="text-sm font-medium text-gray-900">Recorte geográfico</h4>
            <p className="mt-2 text-sm text-gray-700">{paper.geographic_scope}</p>
          </section>
        )}

        {paper.cited_references?.length > 0 && (
          <section>
            <h4 className="text-sm font-medium text-gray-900">Referências citadas</h4>
            <ul className="mt-2 list-disc pl-4 text-sm text-gray-700">
              {paper.cited_references.map((r, i) => (
                <li key={i}>{r}</li>
              ))}
            </ul>
          </section>
        )}

        {paper.citations.length > 0 && (
          <section>
            <h4 className="text-sm font-medium text-gray-900">Trechos fonte</h4>
            <ul className="mt-2 space-y-2">
              {paper.citations.map((c, i) => (
                <li key={i} className="rounded-lg bg-gray-50 p-3 text-xs text-gray-700">
                  <span className="font-medium capitalize">{c.field}: </span>
                  <span className="italic">&quot;{c.source_text}&quot;</span>
                </li>
              ))}
            </ul>
          </section>
        )}
      </div>
    </div>
  );
}
