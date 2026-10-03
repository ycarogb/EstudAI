"use client";

import { Fragment, useState } from "react";
import { ChevronDown, ChevronUp, AlertCircle, CheckCircle2 } from "lucide-react";
import type { PDFPaperResult } from "@/lib/types";

type Props = {
  papers: PDFPaperResult[];
};

const COLS = [
  { key: "objectives" as const, label: "Objetivos" },
  { key: "methodology" as const, label: "Metodologia" },
  { key: "results" as const, label: "Resultados" },
  { key: "gaps" as const, label: "Lacunas" },
] as const;

export function PdfAnalysisTable({ papers }: Props) {
  const [expanded, setExpanded] = useState<string | null>(null);
  const [visibleCols, setVisibleCols] = useState<Set<string>>(
    new Set(["objectives", "methodology", "results", "gaps"])
  );

  const toggle = (col: string) => {
    setVisibleCols((prev) => {
      const next = new Set(prev);
      next.has(col) ? next.delete(col) : next.add(col);
      return next;
    });
  };

  if (papers.length === 0) {
    return (
      <div className="flex h-40 items-center justify-center rounded-xl border border-dashed border-gray-300 bg-white text-sm text-gray-500">
        Aguardando análise dos PDFs...
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2 text-xs text-gray-600">
        <span className="font-medium">Colunas visíveis:</span>
        {COLS.map((c) => (
          <button
            key={c.key}
            onClick={() => toggle(c.key)}
            className={`rounded-full border px-3 py-1 font-medium transition-colors ${
              visibleCols.has(c.key)
                ? "border-brand-500 bg-brand-600 text-white"
                : "border-gray-300 bg-white text-gray-600 hover:bg-gray-50"
            }`}
          >
            {c.label}
          </button>
        ))}
      </div>

      <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
                  Trabalho
                </th>
                {COLS.filter((c) => visibleCols.has(c.key)).map((c) => (
                  <th
                    key={c.key}
                    className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500 min-w-[200px]"
                  >
                    {c.label}
                  </th>
                ))}
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {papers.map((paper) => (
                <Fragment key={paper.filename}>
                  <tr
                    className="cursor-pointer hover:bg-gray-50"
                    onClick={() =>
                      setExpanded(expanded === paper.filename ? null : paper.filename)
                    }
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-start gap-2">
                        {paper.error ? (
                          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" />
                        ) : (
                          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-green-500" />
                        )}
                        <div>
                          <p className="font-medium text-gray-900 line-clamp-2 max-w-xs">
                            {paper.title}
                          </p>
                          {paper.authors.length > 0 && (
                            <p className="mt-0.5 text-xs text-gray-500 line-clamp-1">
                              {paper.authors.slice(0, 3).join(", ")}
                              {paper.authors.length > 3 ? " et al." : ""}
                            </p>
                          )}
                          {paper.year && (
                            <span className="mt-1 inline-block rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-600">
                              {paper.year}
                            </span>
                          )}
                        </div>
                      </div>
                    </td>

                    {COLS.filter((c) => visibleCols.has(c.key)).map((c) => (
                      <td key={c.key} className="px-4 py-3 text-xs text-gray-600">
                        {paper.error ? (
                          <span className="italic text-amber-600">{paper.error}</span>
                        ) : paper[c.key] ? (
                          <span className="line-clamp-4">{paper[c.key]}</span>
                        ) : (
                          <span className="text-gray-300">—</span>
                        )}
                      </td>
                    ))}

                    <td className="px-4 py-3 text-gray-400">
                      {expanded === paper.filename ? (
                        <ChevronUp className="h-4 w-4" />
                      ) : (
                        <ChevronDown className="h-4 w-4" />
                      )}
                    </td>
                  </tr>

                  {expanded === paper.filename && !paper.error && (
                    <tr className="bg-gray-50">
                      <td
                        colSpan={2 + COLS.filter((c) => visibleCols.has(c.key)).length}
                        className="px-6 py-4"
                      >
                        <div className="grid grid-cols-1 gap-4 text-sm sm:grid-cols-2">
                          {COLS.map((c) =>
                            paper[c.key] ? (
                              <div key={c.key}>
                                <p className="font-semibold text-gray-800">{c.label}</p>
                                <p className="mt-1 text-gray-700 leading-relaxed">
                                  {paper[c.key]}
                                </p>
                              </div>
                            ) : null
                          )}
                        </div>

                        {paper.citations.length > 0 && (
                          <div className="mt-4">
                            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                              Trechos fonte
                            </p>
                            <ul className="mt-2 space-y-1">
                              {paper.citations.map((c, i) => (
                                <li
                                  key={i}
                                  className="rounded-lg bg-white px-3 py-2 text-xs text-gray-600 shadow-sm"
                                >
                                  <span className="font-medium capitalize">{c.field}: </span>
                                  <span className="italic">&quot;{c.source_text}&quot;</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
