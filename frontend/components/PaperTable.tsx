"use client";

import { useState, Fragment } from "react";
import type { Paper } from "@/lib/types";
import { TEXT_SOURCE_BADGE, TEXT_SOURCE_LABELS } from "@/lib/types";
import { getSourceLabel } from "@/lib/api";
import { ExternalLink, ChevronDown, ChevronUp } from "lucide-react";

export type ColumnKey =
  | "objectives"
  | "results"
  | "gaps"
  | "methods"
  | "scope"
  | "geographic_scope";

export const COLUMN_LABELS: Record<ColumnKey, string> = {
  objectives: "Objetivos",
  results: "Resultados",
  gaps: "Lacunas",
  methods: "Métodos",
  scope: "Escopo",
  geographic_scope: "Recorte geográfico",
};

export const ALL_COLUMNS: ColumnKey[] = [
  "objectives",
  "results",
  "gaps",
  "methods",
  "scope",
  "geographic_scope",
];

type Props = {
  papers: Paper[];
  onSelectPaper?: (paper: Paper) => void;
  selectedPaperId?: string | null;
  visibleColumns: ColumnKey[];
};

export function PaperTable({
  papers,
  onSelectPaper,
  selectedPaperId,
  visibleColumns,
}: Props) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  if (papers.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center rounded-xl border border-dashed border-gray-300 bg-white">
        <p className="text-sm text-gray-500">
          Nenhum trabalho encontrado. Importe uma coleção Mendeley ou use o chat para buscar.
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left font-medium text-gray-600">Título</th>
              <th className="px-4 py-3 text-left font-medium text-gray-600">Ano</th>
              <th className="px-4 py-3 text-left font-medium text-gray-600">Fonte</th>
              {visibleColumns.length > 0 && (
                <th className="px-4 py-3 text-left font-medium text-gray-600">Análise</th>
              )}
              {visibleColumns.map((col) => (
                <th key={col} className="px-4 py-3 text-left font-medium text-gray-600 min-w-[180px]">
                  {COLUMN_LABELS[col]}
                </th>
              ))}
              <th className="px-4 py-3 text-left font-medium text-gray-600">Ações</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {papers.map((paper) => (
              <Fragment key={paper.id}>
                <tr
                  className={`hover:bg-gray-50 cursor-pointer ${
                    selectedPaperId === paper.id ? "bg-brand-50" : ""
                  }`}
                  onClick={() => onSelectPaper?.(paper)}
                >
                  <td className="px-4 py-3">
                    <div className="font-medium text-gray-900 line-clamp-2 max-w-md">
                      {paper.title}
                    </div>
                    <div className="mt-1 text-xs text-gray-500 line-clamp-1">
                      {paper.authors.slice(0, 3).join(", ")}
                      {paper.authors.length > 3 && " et al."}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-gray-600">{paper.year || "—"}</td>
                  <td className="px-4 py-3">
                    <span className="inline-flex rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-700">
                      {getSourceLabel(paper.source)}
                    </span>
                  </td>
                  {visibleColumns.length > 0 && (
                    <td className="px-4 py-3">
                      {paper.text_source ? (
                        <span
                          className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                            TEXT_SOURCE_BADGE[paper.text_source] ?? "bg-gray-100 text-gray-500"
                          }`}
                          title={TEXT_SOURCE_LABELS[paper.text_source] ?? paper.text_source}
                        >
                          {TEXT_SOURCE_LABELS[paper.text_source] ?? paper.text_source}
                        </span>
                      ) : (
                        <span className="text-xs text-gray-400 italic">—</span>
                      )}
                    </td>
                  )}
                  {visibleColumns.map((col) => (
                    <td key={col} className="px-4 py-3 text-gray-600">
                      {paper[col] ? (
                        <span className="line-clamp-3 text-xs">{paper[col]}</span>
                      ) : (
                        <span className="text-xs text-gray-400 italic">—</span>
                      )}
                    </td>
                  ))}
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      {paper.url && (
                        <a
                          href={paper.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={(e) => e.stopPropagation()}
                          className="text-brand-600 hover:text-brand-700"
                        >
                          <ExternalLink className="h-4 w-4" />
                        </a>
                      )}
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setExpandedId(expandedId === paper.id ? null : paper.id);
                        }}
                        className="text-gray-400 hover:text-gray-600"
                      >
                        {expandedId === paper.id ? (
                          <ChevronUp className="h-4 w-4" />
                        ) : (
                          <ChevronDown className="h-4 w-4" />
                        )}
                      </button>
                    </div>
                  </td>
                </tr>
                {expandedId === paper.id && (
                  <tr className="bg-gray-50">
                    <td colSpan={4 + visibleColumns.length + (visibleColumns.length > 0 ? 1 : 0)} className="px-4 py-3">
                      <div className="text-xs text-gray-700 space-y-2">
                        {paper.abstract && (
                          <div>
                            <span className="font-medium">Resumo: </span>
                            {paper.abstract.slice(0, 500)}
                            {paper.abstract.length > 500 && "..."}
                          </div>
                        )}
                        {paper.cited_references?.length > 0 && (
                          <div>
                            <span className="font-medium">Referências citadas:</span>
                            <ul className="mt-1 list-disc pl-4">
                              {paper.cited_references.slice(0, 8).map((r, i) => (
                                <li key={i}>{r}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                        {paper.citations.length > 0 && (
                          <div>
                            <span className="font-medium">Trechos fonte:</span>
                            <ul className="mt-1 list-disc pl-4">
                              {paper.citations.map((c, i) => (
                                <li key={i} className="italic">
                                  &quot;{c.source_text}&quot;
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
