from enum import Enum

from pydantic import BaseModel, Field


class PaperSource(str, Enum):
    OPENALEX = "openalex"
    SEMANTIC_SCHOLAR = "semantic_scholar"
    BDTD = "bdtd"
    IMPORT = "import"
    MENDELEY = "mendeley"
    SCOPUS = "scopus"
    WOS = "wos"


class CitationSpan(BaseModel):
    field: str
    text: str
    source_text: str


class TextSource(str, Enum):
    PDF_LOCAL = "pdf_local"       # PDF enviado pelo usuário
    PDF_OPEN = "pdf_open"         # PDF de acesso aberto (URL)
    ABSTRACT = "abstract"         # Somente resumo (abstract)
    CROSSREF_ABSTRACT = "crossref_abstract"  # Resumo via Crossref
    METADATA_ONLY = "metadata_only"          # Apenas título/autores


TEXT_SOURCE_LABELS: dict[str, str] = {
    "pdf_local": "Texto completo (PDF local)",
    "pdf_open": "Texto completo (PDF aberto)",
    "abstract": "Resumo",
    "crossref_abstract": "Resumo (Crossref)",
    "metadata_only": "Somente metadados",
}


class Paper(BaseModel):
    id: str
    source: PaperSource
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    abstract: str | None = None
    doi: str | None = None
    url: str | None = None
    pdf_url: str | None = None
    keywords: list[str] = Field(default_factory=list)
    document_type: str | None = None
    # Indica como a análise foi feita
    text_source: str | None = None
    # Campos extraídos por LLM
    objectives: str | None = None
    results: str | None = None
    gaps: str | None = None
    methods: str | None = None
    scope: str | None = None
    geographic_scope: str | None = None
    cited_references: list[str] = Field(default_factory=list)
    citations: list[CitationSpan] = Field(default_factory=list)
    relevance_score: float | None = None


class SearchFilters(BaseModel):
    year_from: int | None = None
    year_to: int | None = None
    sources: list[PaperSource] | None = None
    limit: int = 25


class SearchRequest(BaseModel):
    query: str
    filters: SearchFilters = Field(default_factory=SearchFilters)


class SearchResponse(BaseModel):
    papers: list[Paper]
    total: int
    query_used: str


class ProjectCreate(BaseModel):
    title: str
    query: str


class ProjectResponse(BaseModel):
    id: str
    title: str
    query: str
    created_at: str
    paper_count: int = 0


class ChatRequest(BaseModel):
    message: str
    project_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    papers: list[Paper] = Field(default_factory=list)
    project_id: str | None = None
    action: str | None = None


class ExtractRequest(BaseModel):
    paper_ids: list[str]
    fields: list[str] = Field(default=["objectives", "results", "gaps"])


class ExtractResponse(BaseModel):
    papers: list[Paper]


class SynthesisResponse(BaseModel):
    summary: str
    gaps: list[str]
    themes: list[str]


class SharedReference(BaseModel):
    reference: str
    count: int
    papers: list[dict]


class CorrelationInsight(BaseModel):
    category: str
    title: str
    description: str
    papers: list[str] = Field(default_factory=list)


class CollectionAnalysisResponse(BaseModel):
    total_papers: int
    analyzed_papers: int
    papers_with_text: int = 0
    papers_without_text: int = 0
    coverage_percent: int = 0
    # Breakdown por tipo de fonte textual
    text_source_breakdown: dict[str, int] = Field(default_factory=dict)
    gaps_summary: list[str] = Field(default_factory=list)
    methods_summary: list[str] = Field(default_factory=list)
    scopes_summary: list[str] = Field(default_factory=list)
    geographic_scopes_summary: list[str] = Field(default_factory=list)
    shared_references: list[SharedReference] = Field(default_factory=list)
    narrative_summary: str | None = None
    # Correlações e relações entre os trabalhos
    correlations: list[CorrelationInsight] = Field(default_factory=list)


MENDELEY_EXTRACTION_FIELDS = [
    "objectives",
    "results",
    "gaps",
    "methods",
    "scope",
    "geographic_scope",
    "cited_references",
]

MAX_PDF_FILES = 50

CORRELATION_CATEGORIES = {
    "conclusoes_comuns": "Conclusões comuns",
    "lacunas_comuns": "Lacunas comuns",
    "padroes_metodologicos": "Padrões metodológicos",
    "divergencias": "Divergências",
    "tendencias": "Tendências",
    "insights": "Insights",
}


class PDFPaperResult(BaseModel):
    filename: str
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    objectives: str | None = None
    methodology: str | None = None
    results: str | None = None
    gaps: str | None = None
    citations: list[CitationSpan] = Field(default_factory=list)
    error: str | None = None


class PDFBatchAnalysisResponse(BaseModel):
    papers: list[PDFPaperResult]
    total: int
    analyzed: int
    correlations: list[CorrelationInsight]
    narrative: str


class PdfAnalysisChatMessage(BaseModel):
    role: str
    content: str


class PdfAnalysisChatRequest(BaseModel):
    message: str
    papers: list[PDFPaperResult]
    correlations: list[CorrelationInsight] = Field(default_factory=list)
    narrative: str = ""
    history: list[PdfAnalysisChatMessage] = Field(default_factory=list)


class PdfAnalysisChatResponse(BaseModel):
    reply: str


class PdfAnalysisExportRequest(BaseModel):
    papers: list[PDFPaperResult]
    correlations: list[CorrelationInsight] = Field(default_factory=list)
    narrative: str = ""


class PdfAnalysisCreate(BaseModel):
    title: str | None = None
    papers: list[PDFPaperResult]
    correlations: list[CorrelationInsight] = Field(default_factory=list)
    narrative: str = ""
    analyzed: int = 0
    total: int = 0


class PdfAnalysisSummary(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    total: int
    analyzed: int
    paper_count: int


class PdfAnalysisDetail(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    papers: list[PDFPaperResult]
    correlations: list[CorrelationInsight]
    narrative: str
    analyzed: int
    total: int
    messages: list[PdfAnalysisChatMessage] = Field(default_factory=list)


class PdfAnalysisChatPersistRequest(BaseModel):
    message: str
