export type CitationSpan = {
  field: string;
  text: string;
  source_text: string;
};

export type Paper = {
  id: string;
  source: string;
  title: string;
  authors: string[];
  year: number | null;
  abstract: string | null;
  doi: string | null;
  url: string | null;
  pdf_url: string | null;
  keywords: string[];
  document_type: string | null;
  /** Como a análise foi feita: pdf_local | pdf_open | abstract | crossref_abstract | metadata_only */
  text_source: string | null;
  objectives: string | null;
  results: string | null;
  gaps: string | null;
  methods: string | null;
  scope: string | null;
  geographic_scope: string | null;
  cited_references: string[];
  citations: CitationSpan[];
  relevance_score: number | null;
};

export type ChatMessage = {
  id?: string;
  role: "user" | "assistant";
  content: string;
  created_at?: string;
};

export type Project = {
  id: string;
  title: string;
  query: string;
  created_at: string;
  paper_count: number;
};

export type Synthesis = {
  summary: string;
  gaps: string[];
  themes: string[];
};

export type SharedReference = {
  reference: string;
  count: number;
  papers: { id: string; title: string; year: number | null }[];
};

export type PDFPaperResult = {
  filename: string;
  title: string;
  authors: string[];
  year: number | null;
  objectives: string | null;
  methodology: string | null;
  results: string | null;
  gaps: string | null;
  citations: CitationSpan[];
  error: string | null;
};

export type CorrelationInsight = {
  category: string;
  title: string;
  description: string;
  papers: string[];
};

export type PDFAnalysisState = {
  status: "idle" | "uploading" | "processing" | "correlating" | "done" | "error";
  total: number;
  current: number;
  currentFilename: string;
  papers: PDFPaperResult[];
  correlations: CorrelationInsight[];
  narrative: string;
  analyzed: number;
  errorMessage?: string;
};

export type PdfAnalysisSummary = {
  id: string;
  title: string;
  paper_count: number;
  total: number;
  analyzed: number;
  created_at: string;
  updated_at: string;
};

export type PdfAnalysisDetail = {
  id: string;
  title: string;
  papers: PDFPaperResult[];
  correlations: CorrelationInsight[];
  narrative: string;
  analyzed: number;
  total: number;
  messages: ChatMessage[];
  created_at: string;
  updated_at: string;
};

export const CORRELATION_CATEGORY_LABELS: Record<string, string> = {
  conclusoes_comuns: "Conclusões comuns",
  lacunas_comuns: "Lacunas comuns",
  padroes_metodologicos: "Padrões metodológicos",
  divergencias: "Divergências",
  tendencias: "Tendências",
  insights: "Insights",
};

export const CORRELATION_CATEGORY_COLORS: Record<string, string> = {
  conclusoes_comuns: "bg-green-100 text-green-800 border-green-200",
  lacunas_comuns: "bg-red-100 text-red-800 border-red-200",
  padroes_metodologicos: "bg-blue-100 text-blue-800 border-blue-200",
  divergencias: "bg-amber-100 text-amber-800 border-amber-200",
  tendencias: "bg-purple-100 text-purple-800 border-purple-200",
  insights: "bg-gray-100 text-gray-800 border-gray-200",
};

export type CollectionAnalysis = {
  total_papers: number;
  analyzed_papers: number;
  papers_with_text: number;
  papers_without_text: number;
  coverage_percent: number;
  /** Contagem por tipo de fonte: { pdf_local: N, abstract: N, ... } */
  text_source_breakdown: Record<string, number>;
  gaps_summary: string[];
  methods_summary: string[];
  scopes_summary: string[];
  geographic_scopes_summary: string[];
  shared_references: SharedReference[];
  narrative_summary: string | null;
  correlations: CorrelationInsight[];
};

export const TEXT_SOURCE_LABELS: Record<string, string> = {
  pdf_local: "Texto completo (PDF local)",
  pdf_open: "Texto completo (PDF aberto)",
  abstract: "Resumo",
  crossref_abstract: "Resumo (Crossref)",
  metadata_only: "Somente metadados",
};

export const TEXT_SOURCE_BADGE: Record<string, string> = {
  pdf_local: "bg-green-100 text-green-800",
  pdf_open: "bg-emerald-100 text-emerald-800",
  abstract: "bg-blue-100 text-blue-800",
  crossref_abstract: "bg-sky-100 text-sky-800",
  metadata_only: "bg-gray-100 text-gray-500",
};
