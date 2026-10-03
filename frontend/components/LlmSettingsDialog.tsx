"use client";

import { useCallback, useEffect, useState } from "react";
import clsx from "clsx";
import {
  CheckCircle2,
  ExternalLink,
  Eye,
  EyeOff,
  KeyRound,
  Loader2,
  ShieldCheck,
  X,
  XCircle,
} from "lucide-react";
import { Button } from "./Button";
import { getLlmStatus, testLlmConnection } from "@/lib/api";
import {
  LLM_PROVIDERS,
  type LlmProvider,
  type LlmSettings,
  clearLlmSettings,
  getProviderInfo,
  loadLlmSettings,
  onOpenLlmSettings,
  saveLlmSettings,
} from "@/lib/llmSettings";

type TestResult = { ok: boolean; message: string } | null;

export function LlmSettingsDialog() {
  const [open, setOpen] = useState(false);
  const [provider, setProvider] = useState<LlmProvider>("gemini");
  const [model, setModel] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [hasSaved, setHasSaved] = useState(false);
  const [defaultModels, setDefaultModels] = useState<Record<string, string>>({});
  const [serverConfigured, setServerConfigured] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<TestResult>(null);

  const openDialog = useCallback(() => {
    const saved = loadLlmSettings();
    setProvider(saved?.provider ?? "gemini");
    setModel(saved?.model ?? "");
    setApiKey(saved?.apiKey ?? "");
    setHasSaved(Boolean(saved));
    setShowKey(false);
    setTestResult(null);
    setOpen(true);
    getLlmStatus()
      .then((status) => {
        setDefaultModels(status.default_models);
        setServerConfigured(status.server_configured);
      })
      .catch(() => setServerConfigured(false));
  }, []);

  useEffect(() => onOpenLlmSettings(openDialog), [openDialog]);

  useEffect(() => {
    if (!open) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [open]);

  if (!open) return null;

  const info = getProviderInfo(provider);
  const currentSettings = (): LlmSettings => ({
    provider,
    model: model.trim(),
    apiKey: apiKey.trim(),
  });

  const handleProviderChange = (next: LlmProvider) => {
    if (next === provider) return;
    setProvider(next);
    setModel("");
    setTestResult(null);
  };

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const result = await testLlmConnection(currentSettings());
      setTestResult({
        ok: true,
        message: `Conexão funcionando com ${info.label}${result.model ? ` (${result.model})` : ""}.`,
      });
    } catch (err) {
      setTestResult({
        ok: false,
        message: err instanceof Error ? err.message : "Falha ao testar a conexão.",
      });
    } finally {
      setTesting(false);
    }
  };

  const handleSave = () => {
    saveLlmSettings(currentSettings());
    setOpen(false);
  };

  const handleRemove = () => {
    clearLlmSettings();
    setApiKey("");
    setModel("");
    setHasSaved(false);
    setTestResult(null);
  };

  const canSubmit = apiKey.trim().length > 0 && !testing;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/50 p-4 backdrop-blur-sm"
      onClick={() => setOpen(false)}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="llm-settings-title"
        className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-2xl bg-white shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between border-b border-gray-100 px-6 py-5">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-brand-600 to-violet-600 text-white">
              <KeyRound className="h-5 w-5" />
            </div>
            <div>
              <h2 id="llm-settings-title" className="text-base font-semibold text-gray-900">
                Configurar IA
              </h2>
              <p className="text-xs text-gray-500">Use a sua própria chave, do provedor que preferir</p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setOpen(false)}
            className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
            aria-label="Fechar"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="space-y-5 px-6 py-5">
          {serverConfigured && !hasSaved && (
            <p className="rounded-lg bg-emerald-50 px-3 py-2 text-xs text-emerald-800">
              Este servidor já possui uma chave padrão. Informar a sua é opcional.
            </p>
          )}

          <fieldset>
            <legend className="mb-2 text-xs font-medium uppercase tracking-wide text-gray-500">
              Provedor
            </legend>
            <div className="grid grid-cols-2 gap-2">
              {LLM_PROVIDERS.map((p) => (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => handleProviderChange(p.id)}
                  className={clsx(
                    "rounded-xl border p-3 text-left transition",
                    provider === p.id
                      ? "border-brand-500 bg-brand-50 ring-2 ring-brand-500/20"
                      : "border-gray-200 hover:border-gray-300 hover:bg-gray-50"
                  )}
                >
                  <span className="block text-sm font-medium text-gray-900">{p.label}</span>
                  <span className="mt-0.5 block text-xs text-gray-500">{p.description}</span>
                </button>
              ))}
            </div>
          </fieldset>

          <div>
            <div className="mb-1.5 flex items-center justify-between">
              <label htmlFor="llm-api-key" className="text-xs font-medium uppercase tracking-wide text-gray-500">
                Chave de API
              </label>
              <a
                href={info.keyUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-xs font-medium text-brand-600 hover:text-brand-700"
              >
                Obter chave <ExternalLink className="h-3 w-3" />
              </a>
            </div>
            <div className="relative">
              <input
                id="llm-api-key"
                type={showKey ? "text" : "password"}
                value={apiKey}
                onChange={(e) => {
                  setApiKey(e.target.value);
                  setTestResult(null);
                }}
                placeholder={info.keyPlaceholder}
                autoComplete="off"
                spellCheck={false}
                className="w-full rounded-lg border border-gray-300 py-2 pl-3 pr-10 font-mono text-sm text-gray-900 placeholder:text-gray-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
              />
              <button
                type="button"
                onClick={() => setShowKey((v) => !v)}
                className="absolute inset-y-0 right-0 flex items-center px-3 text-gray-400 hover:text-gray-600"
                aria-label={showKey ? "Ocultar chave" : "Mostrar chave"}
              >
                {showKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>

          <div>
            <label htmlFor="llm-model" className="mb-1.5 block text-xs font-medium uppercase tracking-wide text-gray-500">
              Modelo <span className="normal-case text-gray-400">(opcional)</span>
            </label>
            <input
              id="llm-model"
              type="text"
              value={model}
              onChange={(e) => {
                setModel(e.target.value);
                setTestResult(null);
              }}
              placeholder={defaultModels[provider] ? `Padrão: ${defaultModels[provider]}` : "Modelo padrão do provedor"}
              spellCheck={false}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-sm text-gray-900 placeholder:text-gray-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
            />
          </div>

          {testResult && (
            <div
              className={clsx(
                "flex items-start gap-2 rounded-lg px-3 py-2 text-xs",
                testResult.ok ? "bg-emerald-50 text-emerald-800" : "bg-red-50 text-red-700"
              )}
            >
              {testResult.ok ? (
                <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
              ) : (
                <XCircle className="mt-0.5 h-4 w-4 shrink-0" />
              )}
              <span className="break-words">{testResult.message}</span>
            </div>
          )}

          <div className="flex items-start gap-2 rounded-lg bg-gray-50 px-3 py-2.5 text-xs text-gray-600">
            <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
            <span>
              Sua chave fica salva apenas neste navegador. Ela é enviada ao servidor do EstudAI somente
              durante as análises e nunca é armazenada nem registrada em logs.
            </span>
          </div>
        </div>

        <div className="flex items-center justify-between gap-2 border-t border-gray-100 px-6 py-4">
          {hasSaved ? (
            <Button variant="ghost" onClick={handleRemove} className="text-red-600 hover:bg-red-50">
              Remover chave
            </Button>
          ) : (
            <span />
          )}
          <div className="flex gap-2">
            <Button variant="secondary" onClick={handleTest} disabled={!canSubmit} className="gap-2">
              {testing && <Loader2 className="h-4 w-4 animate-spin" />}
              Testar conexão
            </Button>
            <Button onClick={handleSave} disabled={!canSubmit}>
              Salvar
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
