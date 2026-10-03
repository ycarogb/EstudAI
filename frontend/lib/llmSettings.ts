import { useEffect, useState } from "react";

export type LlmProvider = "openai" | "gemini" | "anthropic" | "openrouter";

export type LlmSettings = {
  provider: LlmProvider;
  model: string;
  apiKey: string;
};

export type LlmProviderInfo = {
  id: LlmProvider;
  label: string;
  shortLabel: string;
  description: string;
  keyUrl: string;
  keyPlaceholder: string;
};

export const LLM_PROVIDERS: LlmProviderInfo[] = [
  {
    id: "gemini",
    label: "Google Gemini",
    shortLabel: "Gemini",
    description: "Possui camada gratuita",
    keyUrl: "https://aistudio.google.com/apikey",
    keyPlaceholder: "AIza...",
  },
  {
    id: "openai",
    label: "OpenAI",
    shortLabel: "OpenAI",
    description: "Família GPT-5",
    keyUrl: "https://platform.openai.com/api-keys",
    keyPlaceholder: "sk-...",
  },
  {
    id: "anthropic",
    label: "Anthropic Claude",
    shortLabel: "Claude",
    description: "Sonnet, Opus e Haiku",
    keyUrl: "https://console.anthropic.com/settings/keys",
    keyPlaceholder: "sk-ant-...",
  },
  {
    id: "openrouter",
    label: "OpenRouter",
    shortLabel: "OpenRouter",
    description: "Centenas de modelos, inclusive gratuitos",
    keyUrl: "https://openrouter.ai/keys",
    keyPlaceholder: "sk-or-...",
  },
];

const STORAGE_KEY = "estudai.llm-settings";
const CHANGED_EVENT = "estudai:llm-settings-changed";
const OPEN_EVENT = "estudai:open-llm-settings";

export function getProviderInfo(provider: LlmProvider): LlmProviderInfo {
  return LLM_PROVIDERS.find((p) => p.id === provider) ?? LLM_PROVIDERS[0];
}

function isValidSettings(value: unknown): value is LlmSettings {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Partial<LlmSettings>;
  return (
    LLM_PROVIDERS.some((p) => p.id === candidate.provider) &&
    typeof candidate.apiKey === "string" &&
    candidate.apiKey.length > 0 &&
    typeof candidate.model === "string"
  );
}

function parseStoredSettings(raw: string): unknown {
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function loadLlmSettings(): LlmSettings | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  const parsed = parseStoredSettings(raw);
  return isValidSettings(parsed) ? parsed : null;
}

export function saveLlmSettings(settings: LlmSettings) {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
  window.dispatchEvent(new Event(CHANGED_EVENT));
}

export function clearLlmSettings() {
  window.localStorage.removeItem(STORAGE_KEY);
  window.dispatchEvent(new Event(CHANGED_EVENT));
}

export function llmHeaders(settings: LlmSettings | null = loadLlmSettings()): Record<string, string> {
  if (!settings) return {};
  return {
    "X-LLM-Provider": settings.provider,
    "X-LLM-Model": settings.model,
    "X-LLM-Api-Key": settings.apiKey,
  };
}

export function openLlmSettings() {
  window.dispatchEvent(new Event(OPEN_EVENT));
}

export function onOpenLlmSettings(callback: () => void): () => void {
  window.addEventListener(OPEN_EVENT, callback);
  return () => window.removeEventListener(OPEN_EVENT, callback);
}

export function useLlmSettings(): LlmSettings | null {
  const [settings, setSettings] = useState<LlmSettings | null>(null);

  useEffect(() => {
    const refresh = () => setSettings(loadLlmSettings());
    refresh();
    window.addEventListener(CHANGED_EVENT, refresh);
    window.addEventListener("storage", refresh);
    return () => {
      window.removeEventListener(CHANGED_EVENT, refresh);
      window.removeEventListener("storage", refresh);
    };
  }, []);

  return settings;
}
