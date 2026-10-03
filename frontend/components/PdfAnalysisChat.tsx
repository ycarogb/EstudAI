"use client";

import { useEffect, useRef, useState } from "react";
import { MessageCircle, Send, X } from "lucide-react";
import { chatPdfAnalysisPersisted } from "@/lib/api";
import type { ChatMessage, CorrelationInsight, PDFPaperResult } from "@/lib/types";
import { Button } from "./Button";

type Props = {
  analysisId: string;
  papers: PDFPaperResult[];
  correlations: CorrelationInsight[];
  narrative: string;
  initialMessages?: ChatMessage[];
  onClose: () => void;
};

const SUGGESTIONS = [
  "Quais lacunas em comum aparecem entre os estudos?",
  "Como posso usar essa coleção na minha proposta de tese?",
  "Quais metodologias se repetem e qual faz mais sentido para mim?",
  "Onde os trabalhos discordam e o que isso significa?",
];

export function PdfAnalysisChat({
  analysisId,
  papers,
  correlations,
  narrative,
  initialMessages = [],
  onClose,
}: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, [messages, loading]);

  const handleSend = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || loading) return;

    const userMsg: ChatMessage = { role: "user", content: trimmed };
    const nextHistory = [...messages, userMsg];
    setMessages(nextHistory);
    setLoading(true);
    setError(null);

    try {
      const { reply } = await chatPdfAnalysisPersisted(analysisId, trimmed);
      setMessages([...nextHistory, { role: "assistant", content: reply }]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao enviar mensagem");
      setMessages(messages);
    } finally {
      setLoading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleSend(inputRef.current?.value ?? "");
  };

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden bg-white">
      <div className="flex shrink-0 items-center justify-between border-b border-gray-200 bg-brand-600 px-5 py-4 text-white">
        <div>
          <p className="text-base font-semibold">Assistente metodológico</p>
          <p className="text-sm text-brand-100">
            {papers.length} trabalho{papers.length !== 1 ? "s" : ""} na análise
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="rounded-lg p-2 hover:bg-brand-700"
          aria-label="Fechar chat"
        >
          <X className="h-5 w-5" />
        </button>
      </div>

      <div
        ref={scrollRef}
        className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-5 py-5 space-y-4 bg-gray-50"
      >
        {messages.length === 0 && (
          <div className="rounded-xl border border-gray-200 bg-white p-5 text-sm text-gray-700 shadow-sm">
            <p className="text-base font-medium text-gray-900">
              Converse sobre os estudos analisados
            </p>
            <p className="mt-2 text-sm text-gray-500">
              Pergunte sobre objetivos, lacunas, metodologias — respostas diretas, com resumo no final.
            </p>
            <div className="mt-4 space-y-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => handleSend(s)}
                  disabled={loading}
                  className="block w-full rounded-lg border border-brand-200 bg-brand-50 px-4 py-2.5 text-left text-sm text-brand-800 hover:bg-brand-100 disabled:opacity-50"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[92%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                msg.role === "user"
                  ? "bg-brand-600 text-white"
                  : "bg-white text-gray-800 shadow-sm border border-gray-200"
              }`}
            >
              <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide opacity-70">
                {msg.role === "user" ? "Você" : "Assistente"}
              </p>
              <p className="whitespace-pre-wrap">{msg.content}</p>
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="rounded-2xl border border-gray-200 bg-white px-4 py-3 text-sm text-gray-500 shadow-sm">
              Analisando...
            </div>
          </div>
        )}

        {error && (
          <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
        )}
      </div>

      <form onSubmit={handleSubmit} className="shrink-0 border-t border-gray-200 bg-white p-4">
        <div className="flex gap-3">
          <textarea
            ref={inputRef}
            rows={3}
            placeholder="Pergunte sobre objetivos, lacunas, metodologias..."
            className="flex-1 resize-none rounded-xl border border-gray-300 px-4 py-3 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            disabled={loading}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSubmit(e);
              }
            }}
          />
          <Button type="submit" disabled={loading} className="self-end px-4 py-3">
            <Send className="h-5 w-5" />
          </Button>
        </div>
      </form>
    </div>
  );
}

type FabProps = {
  onClick: () => void;
};

export function PdfAnalysisChatFab({ onClick }: FabProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="fixed bottom-8 right-8 z-40 flex items-center gap-3 rounded-full bg-brand-600 pl-5 pr-6 py-4 text-white shadow-xl transition-all hover:bg-brand-700 hover:shadow-2xl focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
      aria-label="Abrir assistente metodológico"
    >
      <MessageCircle className="h-7 w-7 shrink-0" />
      <span className="text-sm font-semibold">Assistente IA</span>
    </button>
  );
}
