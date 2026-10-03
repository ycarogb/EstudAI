"use client";

import { useEffect, useState } from "react";
import clsx from "clsx";
import { KeyRound } from "lucide-react";
import { getLlmStatus } from "@/lib/api";
import { getProviderInfo, openLlmSettings, useLlmSettings } from "@/lib/llmSettings";

export function LlmSettingsButton({ className }: { className?: string }) {
  const settings = useLlmSettings();
  const [serverConfigured, setServerConfigured] = useState(false);

  useEffect(() => {
    getLlmStatus()
      .then((status) => setServerConfigured(status.server_configured))
      .catch(() => setServerConfigured(false));
  }, []);

  const configured = Boolean(settings) || serverConfigured;
  const label = settings
    ? getProviderInfo(settings.provider).shortLabel
    : serverConfigured
      ? "IA do servidor"
      : "Configurar IA";

  return (
    <button
      type="button"
      onClick={openLlmSettings}
      title={configured ? "IA configurada — clique para alterar" : "Informe sua chave de IA"}
      className={clsx(
        "inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium transition",
        configured
          ? "border-gray-200 bg-white text-gray-700 hover:border-brand-300 hover:bg-brand-50"
          : "border-amber-300 bg-amber-50 text-amber-800 hover:bg-amber-100",
        className
      )}
    >
      <KeyRound className="h-3.5 w-3.5" />
      {label}
      <span
        className={clsx("h-2 w-2 rounded-full", configured ? "bg-emerald-500" : "bg-amber-500")}
        aria-hidden="true"
      />
    </button>
  );
}
