import type {
  ChatMessage,
  CollectionAnalysis,
  CorrelationInsight,
  Paper,
  PDFPaperResult,
  PdfAnalysisDetail,
  PdfAnalysisSummary,
  Project,
  Synthesis,
} from "./types";
import { type LlmSettings, llmHeaders, openLlmSettings } from "./llmSettings";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function parseJson(text: string): { detail?: unknown; code?: unknown } | null {
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

async function responseError(res: Response): Promise<Error> {
  const text = await res.text();
  const body = parseJson(text);
  if (body?.code === "llm_not_configured") openLlmSettings();
  if (typeof body?.detail === "string") return new Error(body.detail);
  return new Error(text || `HTTP ${res.status}`);
}

async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { ...llmHeaders(), ...(init.headers as Record<string, string> | undefined) },
  });
  if (!res.ok) throw await responseError(res);
  return res;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await apiFetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers as Record<string, string> | undefined),
    },
  });
  return res.json();
}

export async function getLlmStatus() {
  return request<{
    server_configured: boolean;
    server_provider: string | null;
    server_model: string | null;
    supported_providers: string[];
    default_models: Record<string, string>;
  }>("/api/llm/status");
}

export async function testLlmConnection(settings: LlmSettings) {
  return request<{ ok: boolean; provider: string; model: string | null }>("/api/llm/test", {
    method: "POST",
    headers: llmHeaders(settings),
  });
}

export async function sendChat(message: string, projectId?: string) {
  return request<{
    reply: string;
    papers: Paper[];
    project_id: string | null;
    action: string | null;
  }>("/api/chat", {
    method: "POST",
    body: JSON.stringify({ message, project_id: projectId }),
  });
}

export async function getProject(id: string) {
  return request<{
    id: string;
    title: string;
    query: string;
    created_at: string;
    papers: Paper[];
    analysis: CollectionAnalysis | null;
    messages: ChatMessage[];
  }>(`/api/projects/${id}`);
}

export async function listProjects() {
  return request<Project[]>("/api/projects");
}

export async function createProject(title: string, query: string) {
  return request<Project>("/api/projects", {
    method: "POST",
    body: JSON.stringify({ title, query }),
  });
}

export async function importMendeley(projectId: string, file: File) {
  const form = new FormData();
  form.append("file", file);
  const res = await apiFetch(`/api/projects/${projectId}/import-mendeley`, {
    method: "POST",
    body: form,
  });
  return res.json() as Promise<{
    imported: number;
    papers: Paper[];
    message: string;
  }>;
}

export async function uploadPdfs(projectId: string, files: File[]) {
  const form = new FormData();
  files.forEach((f) => form.append("files", f));
  const res = await apiFetch(`/api/projects/${projectId}/upload-pdfs`, {
    method: "POST",
    body: form,
  });
  return res.json() as Promise<{
    attached: number;
    unmatched: string[];
    papers: Paper[];
  }>;
}

export async function getTextCoverage(projectId: string) {
  return request<{
    total: number;
    with_text: number;
    without_text: number;
    coverage_percent: number;
    papers: { id: string; title: string; has_text: boolean; text_source: string }[];
  }>(`/api/projects/${projectId}/text-coverage`);
}

export async function analyzeCollection(projectId: string) {
  return request<CollectionAnalysis>(`/api/projects/${projectId}/analyze-collection`, {
    method: "POST",
  });
}

export async function importReferences(projectId: string, file: File) {
  const form = new FormData();
  form.append("file", file);
  const res = await apiFetch(`/api/projects/${projectId}/import`, {
    method: "POST",
    body: form,
  });
  return res.json() as Promise<{ imported: number; papers: Paper[] }>;
}

export async function exportProject(projectId: string, format: "csv" | "bibtex") {
  const res = await apiFetch(`/api/projects/${projectId}/export?format=${format}`);
  return res.text();
}

export async function synthesizeGaps(projectId: string) {
  return request<Synthesis>(`/api/projects/${projectId}/synthesize`, {
    method: "POST",
  });
}

export async function extractPapers(paperIds: string[], fields: string[]) {
  return request<{ papers: Paper[] }>("/api/extract", {
    method: "POST",
    body: JSON.stringify({ paper_ids: paperIds, fields }),
  });
}

export type PDFStreamEvent =
  | { type: "start"; total: number }
  | { type: "progress"; index: number; total: number; filename: string; stage: string }
  | { type: "paper"; index: number; paper: PDFPaperResult }
  | { type: "correlations"; correlations: CorrelationInsight[]; narrative: string }
  | { type: "done"; total: number; analyzed: number }
  | { type: "error"; message: string };

/**
 * Uploads up to 50 PDFs and streams SSE events back.
 * The `onEvent` callback is called for each event received.
 */
export async function analyzePdfs(
  files: File[],
  onEvent: (event: PDFStreamEvent) => void,
  signal?: AbortSignal
): Promise<void> {
  const form = new FormData();
  files.forEach((f) => form.append("files", f));

  const res = await apiFetch("/api/analyze-pdfs", {
    method: "POST",
    body: form,
    signal,
  });

  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      try {
        const event = JSON.parse(line.slice(6)) as PDFStreamEvent;
        onEvent(event);
      } catch {
        // malformed event — skip
      }
    }
  }
}

export async function chatAboutPdfAnalysis(
  message: string,
  context: {
    papers: PDFPaperResult[];
    correlations: CorrelationInsight[];
    narrative: string;
    history: ChatMessage[];
  }
) {
  return request<{ reply: string }>("/api/analyze-pdfs/chat", {
    method: "POST",
    body: JSON.stringify({
      message,
      papers: context.papers,
      correlations: context.correlations,
      narrative: context.narrative,
      history: context.history.map((m) => ({ role: m.role, content: m.content })),
    }),
  });
}

export async function exportPdfAnalysis(data: {
  papers: PDFPaperResult[];
  correlations: CorrelationInsight[];
  narrative: string;
}): Promise<Blob> {
  const res = await apiFetch("/api/analyze-pdfs/export-pdf", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return res.blob();
}

export async function listPdfAnalyses() {
  return request<PdfAnalysisSummary[]>("/api/pdf-analyses");
}

export async function savePdfAnalysis(data: {
  title?: string;
  papers: PDFPaperResult[];
  correlations: CorrelationInsight[];
  narrative: string;
  analyzed: number;
  total: number;
}) {
  return request<PdfAnalysisDetail>("/api/pdf-analyses", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function getPdfAnalysis(analysisId: string) {
  return request<PdfAnalysisDetail>(`/api/pdf-analyses/${analysisId}`);
}

export async function deletePdfAnalysis(analysisId: string) {
  return request<{ ok: boolean }>(`/api/pdf-analyses/${analysisId}`, {
    method: "DELETE",
  });
}

export async function chatPdfAnalysisPersisted(analysisId: string, message: string) {
  return request<{ reply: string }>(`/api/pdf-analyses/${analysisId}/chat`, {
    method: "POST",
    body: JSON.stringify({ message }),
  });
}

export type PdfRetryStreamEvent =
  | {
      type: "start";
      failed_count: number;
      matched: number;
      unmatched: string[];
      pending_filenames: string[];
    }
  | {
      type: "progress";
      index: number;
      total: number;
      filename: string;
      stage: "extracting" | "correlating";
    }
  | { type: "paper"; filename: string; paper: PDFPaperResult }
  | { type: "correlations"; correlations: CorrelationInsight[]; narrative: string }
  | {
      type: "done";
      analyzed: number;
      retried: number;
      still_failed: number;
      analysis: PdfAnalysisDetail | null;
    }
  | { type: "error"; message: string };

export async function retryFailedPdfAnalysis(
  analysisId: string,
  files: File[],
  onEvent: (event: PdfRetryStreamEvent) => void
): Promise<void> {
  const form = new FormData();
  files.forEach((f) => form.append("files", f));

  const res = await apiFetch(`/api/pdf-analyses/${analysisId}/retry-failed`, {
    method: "POST",
    body: form,
  });

  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      try {
        const event = JSON.parse(line.slice(6)) as PdfRetryStreamEvent;
        onEvent(event);
      } catch {
        // skip malformed
      }
    }
  }
}

export function getSourceLabel(source: string): string {
  const labels: Record<string, string> = {
    openalex: "OpenAlex",
    semantic_scholar: "Semantic Scholar",
    bdtd: "BDTD",
    scielo: "SciELO",
    google_scholar: "Google Scholar",
    mendeley: "Mendeley",
    import: "Importado",
    scopus: "Scopus",
    wos: "Web of Science",
  };
  return labels[source] || source;
}
