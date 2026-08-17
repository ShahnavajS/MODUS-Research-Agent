export interface HealthStatus {
  status: string;
  version: string;
  timestamp: string;
  database: {
    status: string;
    dialect: string;
  };
}

export interface ResearchProject {
  id: string;
  name: string;
  description: string | null;
  research_topic: string;
  industry: string | null;
  status: 'draft' | 'active' | 'completed' | 'failed';
  created_at: string;
  updated_at: string;
}

export interface CreateProjectPayload {
  name: string;
  description?: string;
  research_topic: string;
  industry?: string;
  status?: string;
}

export interface UpdateProjectPayload {
  name?: string;
  description?: string;
  research_topic?: string;
  industry?: string;
  status?: string;
}

export interface ResearchQuestion {
  id: string;
  project_id: string;
  question: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface CreateQuestionPayload {
  question: string;
  status?: string;
}

export interface UpdateQuestionPayload {
  question?: string;
  status?: string;
}

export interface ResearchSubQuestion {
  id: string;
  research_run_id: string;
  question: string;
  sequence_number: number;
  status: string;
  created_at: string;
  completed_at: string | null;
}

export interface SourceContent {
  id: string;
  source_id: string;
  content: string;
  content_hash: string | null;
  word_count: number | null;
  extraction_status: string;
  created_at: string;
}

export interface ResearchSource {
  id: string;
  research_run_id: string;
  title: string;
  url: string | null;
  publisher: string | null;
  author: string | null;
  published_at: string | null;
  retrieved_at: string;
  source_type: string;
  credibility_score: number | null;
  metadata_json: Record<string, unknown> | null;
  created_at: string;
  content?: SourceContent | null;
}

export interface Evidence {
  id: string;
  finding_id: string;
  source_id: string;
  source_content_id: string | null;
  excerpt: string;
  relevance_score: number;
  evidence_type: string;
  created_at: string;
  source_title?: string | null;
  source_url?: string | null;
}

export interface Finding {
  id: string;
  research_run_id: string;
  statement: string;
  finding_type: 'fact' | 'trend' | 'claim' | 'observation' | 'prediction' | 'risk' | 'opportunity';
  confidence: number;
  importance: 'low' | 'medium' | 'high' | 'critical';
  created_at: string;
  updated_at: string;
  evidences: Evidence[];
}

export interface Contradiction {
  id: string;
  research_run_id: string;
  finding_a_id: string;
  finding_b_id: string;
  finding_a_statement?: string | null;
  finding_b_statement?: string | null;
  description: string;
  severity: 'low' | 'medium' | 'high';
  resolution_status: 'unresolved' | 'reviewed' | 'resolved';
  resolution_notes: string | null;
  created_at: string;
}

export interface Conclusion {
  id: string;
  research_run_id: string;
  statement: string;
  confidence: number;
  created_at: string;
  updated_at: string;
  finding_ids: string[];
}

export interface RunCounts {
  sub_questions: number;
  sources: number;
  findings: number;
  evidence: number;
  contradictions: number;
  conclusions: number;
}

export interface ResearchRun {
  id: string;
  question_id: string;
  status: 'queued' | 'running' | 'completed' | 'failed';
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
  metadata_json: Record<string, unknown> | null;
  created_at: string;
  counts: RunCounts;
}

export interface ResearchRunDetail extends ResearchRun {
  question_text: string;
  project_id: string;
  project_name: string;
  sub_questions: ResearchSubQuestion[];
  sources: ResearchSource[];
  findings: Finding[];
  contradictions: Contradiction[];
  conclusions: Conclusion[];
}

export interface TraceabilityNode {
  conclusion_id: string;
  conclusion_statement: string;
  conclusion_confidence: number;
  findings: Finding[];
}

export interface RunTraceability {
  run_id: string;
  question_id: string;
  question_text: string;
  status: string;
  execution_metadata: Record<string, unknown> | null;
  provenance_graph: TraceabilityNode[];
}
