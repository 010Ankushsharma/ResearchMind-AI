/**
 * Shared TypeScript types mirroring backend/schemas/*.py.
 * Keep these in sync with the FastAPI Pydantic models.
 */

// ── Enums ────────────────────────────────────────────────────────────────

export type SessionStatus =
  | "pending"
  | "planning"
  | "researching"
  | "extracting"
  | "verifying"
  | "summarizing"
  | "writing_report"
  | "generating_executive_summary"
  | "generating_citations"
  | "exporting_pdf"
  | "completed"
  | "failed";

export type AgentName =
  | "research_coordinator"
  | "web_research"
  | "content_extraction"
  | "fact_verification"
  | "knowledge_base"
  | "summarization"
  | "report_writer"
  | "citation"
  | "executive_summary"
  | "pdf_generation";

export type LogLevel = "info" | "warning" | "error" | "success";

export type CitationStyle = "apa" | "mla" | "ieee";

export type UserRole = "admin" | "member" | "viewer";

// ── User ─────────────────────────────────────────────────────────────────

export interface UserRead {
  id: string;
  clerk_id: string;
  email: string;
  full_name: string | null;
  avatar_url: string | null;
  role: UserRole;
  is_active: boolean;
  research_count: number;
  created_at: string;
  updated_at: string;
}

// ── Research Session ─────────────────────────────────────────────────────

export interface ResearchPlanSubtopic {
  title: string;
  search_queries: string[];
  rationale: string;
}

export interface ResearchPlan {
  main_topic: string;
  research_objective: string;
  subtopics: ResearchPlanSubtopic[];
  suggested_report_sections: string[];
  estimated_source_count: number;
}

export interface ResearchSessionRead {
  id: string;
  user_id: string;
  query: string;
  status: SessionStatus;
  research_plan: ResearchPlan | null;
  progress_percent: number;
  error_message: string | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export interface ResearchSessionSummary {
  id: string;
  query: string;
  status: SessionStatus;
  progress_percent: number;
  created_at: string;
}

export interface ResearchSessionCreate {
  query: string;
  max_sources?: number;
  citation_style?: CitationStyle;
}

// ── Source ───────────────────────────────────────────────────────────────

export interface SourceRead {
  id: string;
  url: string;
  title: string | null;
  domain: string | null;
  snippet: string | null;
  domain_authority_score: number | null;
  source_age_score: number | null;
  citation_count_score: number | null;
  trustworthiness_score: number | null;
  published_date: string | null;
  citation_index: number | null;
}

// ── Agent Log / Status ───────────────────────────────────────────────────

export interface AgentLogRead {
  id: string;
  agent_name: AgentName;
  level: LogLevel;
  message: string;
  details: Record<string, unknown> | null;
  duration_ms: number | null;
  created_at: string;
}

export interface AgentStatusItem {
  agent_name: AgentName;
  is_active: boolean;
  current_task: string | null;
  last_updated: string | null;
}

// ── Report ───────────────────────────────────────────────────────────────

export interface CitationEntry {
  source_id: string;
  formatted: string;
}

export interface ReportRead {
  id: string;
  research_session_id: string;
  user_id: string;
  title: string;

  abstract: string | null;
  introduction: string | null;
  key_findings: string | null;
  analysis: string | null;
  recommendations: string | null;
  conclusion: string | null;

  short_summary: string | null;
  medium_summary: string | null;
  detailed_summary: string | null;

  executive_summary: string | null;
  key_takeaways: string[] | null;
  risks: string[] | null;
  opportunities: string[] | null;

  default_citation_style: CitationStyle;
  pdf_file_path: string | null;
  pdf_generated_at: string | null;
  chart_data: Record<string, unknown> | null;

  version: number;
  created_at: string;
  updated_at: string;
}

export interface ReportSummary {
  id: string;
  research_session_id: string;
  title: string;
  version: number;
  created_at: string;
}

export interface PDFExportRequest {
  report_id: string;
  include_charts?: boolean;
  include_cover_page?: boolean;
  include_table_of_contents?: boolean;
  citation_style?: CitationStyle;
}

export interface PDFExportResponse {
  report_id: string;
  pdf_url: string;
  generated_at: string;
}

// ── History ──────────────────────────────────────────────────────────────

export interface HistoryItem {
  session_id: string;
  query: string;
  status: SessionStatus;
  report_id: string | null;
  report_title: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface HistorySearchResult {
  chroma_vector_id: string;
  text: string;
  metadata: Record<string, unknown>;
  relevance_score: number | null;
}

// ── Analytics ────────────────────────────────────────────────────────────

export interface AnalyticsOverview {
  total_research_sessions: number;
  total_reports_generated: number;
  total_sources_collected: number;
  average_trustworthiness_score: number | null;
  sessions_in_progress: number;
}

export interface ChartDataPoint {
  label: string;
  value: number;
}
