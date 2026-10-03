"use client";

import type { CorrelationInsight } from "@/lib/types";
import { CORRELATION_CATEGORY_COLORS, CORRELATION_CATEGORY_LABELS } from "@/lib/types";
import { Lightbulb } from "lucide-react";

type Props = {
  correlations: CorrelationInsight[];
  narrative: string;
};

const CATEGORY_ORDER = [
  "conclusoes_comuns",
  "lacunas_comuns",
  "padroes_metodologicos",
  "tendencias",
  "divergencias",
  "insights",
];

function groupBy<T>(items: T[], key: (item: T) => string): Record<string, T[]> {
  return items.reduce<Record<string, T[]>>((acc, item) => {
    const k = key(item);
    (acc[k] ??= []).push(item);
    return acc;
  }, {});
}

export function CorrelationsPanel({ correlations, narrative }: Props) {
  if (correlations.length === 0 && !narrative) {
    return (
      <div className="flex h-40 items-center justify-center rounded-xl border border-dashed border-gray-300 bg-white text-sm text-gray-500">
        Correlações disponíveis após a análise completa.
      </div>
    );
  }

  const grouped = groupBy(correlations, (c) => c.category);

  return (
    <div className="space-y-6">
      {narrative && (
        <div className="rounded-xl border border-brand-200 bg-brand-50 p-5">
          <div className="flex items-start gap-3">
            <Lightbulb className="mt-0.5 h-5 w-5 shrink-0 text-brand-600" />
            <div>
              <p className="text-sm font-semibold text-brand-900">Síntese do estado da arte</p>
              <p className="mt-2 text-sm text-brand-800 leading-relaxed">{narrative}</p>
            </div>
          </div>
        </div>
      )}

      {CATEGORY_ORDER.map((cat) => {
        const items = grouped[cat];
        if (!items?.length) return null;
        const label = CORRELATION_CATEGORY_LABELS[cat] ?? cat;
        const colorClass =
          CORRELATION_CATEGORY_COLORS[cat] ?? "bg-gray-100 text-gray-800 border-gray-200";

        return (
          <section key={cat}>
            <div className="mb-3 flex items-center gap-2">
              <span
                className={`inline-flex rounded-full border px-3 py-0.5 text-xs font-semibold ${colorClass}`}
              >
                {label}
              </span>
              <span className="text-xs text-gray-400">
                {items.length} insight{items.length !== 1 ? "s" : ""}
              </span>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              {items.map((insight, i) => (
                <div
                  key={i}
                  className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm"
                >
                  <p className="text-sm font-semibold text-gray-900">{insight.title}</p>
                  <p className="mt-2 text-sm text-gray-700 leading-relaxed">
                    {insight.description}
                  </p>
                  {insight.papers.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-1">
                      {insight.papers.map((p, j) => (
                        <span
                          key={j}
                          className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600"
                        >
                          {p}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </section>
        );
      })}
    </div>
  );
}
