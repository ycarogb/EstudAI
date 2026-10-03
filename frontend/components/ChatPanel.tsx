"use client";

import { useRef, useEffect } from "react";
import type { ChatMessage } from "@/lib/types";
import { Send } from "lucide-react";
import { Button } from "./Button";

type Props = {
  messages: ChatMessage[];
  onSend: (message: string) => void;
  loading?: boolean;
};

export function ChatPanel({ messages, onSend, loading }: Props) {
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const value = inputRef.current?.value.trim();
    if (!value || loading) return;
    onSend(value);
    if (inputRef.current) inputRef.current.value = "";
  };

  return (
    <div className="flex h-full flex-col border-r border-gray-200 bg-gray-50">
      <div className="border-b border-gray-200 px-4 py-3">
        <h2 className="text-sm font-semibold text-gray-900">Assistente</h2>
        <p className="text-xs text-gray-500">Converse para buscar e analisar trabalhos</p>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {messages.length === 0 && (
          <div className="rounded-lg bg-white p-4 text-sm text-gray-600 shadow-sm">
            <p className="font-medium text-gray-800">Sugestões:</p>
            <ul className="mt-2 space-y-1 text-xs">
              <li>• &quot;Busque artigos sobre IA na educação superior&quot;</li>
              <li>• &quot;Importei coleção Mendeley — analise lacunas e métodos&quot;</li>
              <li>• &quot;Quais referências aparecem em mais de um trabalho?&quot;</li>
              <li>• &quot;Extraia escopo e recorte geográfico dos trabalhos&quot;</li>
            </ul>
          </div>
        )}
        {messages.map((msg, i) => (
          <div
            key={msg.id || i}
            className={`rounded-lg px-3 py-2 text-sm ${
              msg.role === "user"
                ? "ml-4 bg-brand-600 text-white"
                : "mr-4 bg-white text-gray-800 shadow-sm"
            }`}
          >
            {msg.content}
          </div>
        ))}
        {loading && (
          <div className="mr-4 rounded-lg bg-white px-3 py-2 text-sm text-gray-500 shadow-sm">
            Analisando...
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <form onSubmit={handleSubmit} className="border-t border-gray-200 p-4">
        <div className="flex gap-2">
          <textarea
            ref={inputRef}
            rows={2}
            placeholder="Descreva o que você precisa..."
            className="flex-1 resize-none rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            disabled={loading}
          />
          <Button type="submit" disabled={loading} className="self-end px-3">
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </form>
    </div>
  );
}
