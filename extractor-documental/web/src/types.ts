export type FieldType =
  | "string"
  | "number"
  | "integer"
  | "date"
  | "enum"
  | "boolean";
export interface FieldSpec {
  name: string;
  type: FieldType;
  description: string;
  required: boolean;
  enum_values: string[];
  minimum?: number | null;
  maximum?: number | null;
}
export interface ExtractionSchema {
  title: string;
  fields: FieldSpec[];
}
export interface SourceDocument {
  id: string;
  name: string;
  mime: string;
  size: number;
  sha256: string;
  warnings: string[];
  text?: string | null;
  preview_url?: string;
}
export interface Session {
  csrf_token: string;
  has_api_key: boolean;
  models: { extractor: string; reviewer: string };
  session_expires_in: number;
  total_usage?: TokenUsage;
  usage_history?: ProviderCall[];
  schema?: ExtractionSchema | null;
  latest_batch_id?: string | null;
}
export interface TokenUsage {
  input_tokens?: number | null;
  output_tokens?: number | null;
  thinking_tokens?: number | null;
  cached_tokens?: number | null;
  total_tokens?: number | null;
  complete?: boolean;
  measured_calls?: number;
  total_calls?: number;
}
export interface ProviderCall {
  id: string;
  document_id: string;
  attempt: number;
  role: "extraction" | "review" | "verification";
  model: string;
  started_at: string;
  elapsed_ms: number;
  usage: TokenUsage;
  status: "completed" | "error" | "not_sent";
  error_code?: string | null;
  batch_id?: string;
}
export interface PipelineEvent {
  document_id: string;
  stage: string;
  attempt: number;
  timestamp: string;
  detail: string;
}
export interface FieldReview {
  field: string;
  status: string;
  evidence: string | null;
  location: string | null;
  problem: string | null;
  severity: string;
  proposed_value: unknown;
  verification_question: string;
}
export interface Verdict {
  decision: string;
  fields: FieldReview[];
  reason: string;
  should_retry: boolean;
}
export interface Attempt {
  attempt: number;
  outcome: string;
  messages?: string[];
  error_type?: string | null;
  record_before?: Record<string, unknown> | null;
  record_after?: Record<string, unknown> | null;
  reviewer_verdict?: Verdict | null;
  [key: string]: unknown;
}
export interface DocumentResult {
  document_id: string;
  source_name: string;
  status: "exitoso" | "parcial" | "fallido";
  record: Record<string, unknown> | null;
  attempts: number;
  review_calls: number;
  reasons: string[];
  attempt_log: Attempt[];
  reviewer_verdict?: Verdict | null;
  human_review_required: boolean;
  usage: TokenUsage;
  [key: string]: unknown;
}
export interface Metrics {
  total: number;
  successful: number;
  partial: number;
  failed: number;
  success_rate: number | null;
  [key: string]: unknown;
}
export interface Batch {
  id: string;
  status: "running" | "completed" | "failed";
  mode: string;
  events: PipelineEvent[];
  results: DocumentResult[];
  metrics: Metrics | null;
  usage: TokenUsage;
  usage_history?: ProviderCall[];
  session_usage?: TokenUsage;
  session_usage_history?: ProviderCall[];
  schema?: ExtractionSchema;
  supervision?: {
    required: boolean;
    reason: string;
    threshold: number;
    processed: number;
    success_rate: number | null;
  };
  human_reviews?: {
    id: string;
    document_id: string;
    timestamp: string;
    note: string;
    proposed_record: Record<string, unknown>;
    validation: { status: string; reasons: string[] };
  }[];
  error?: string | null;
  report?: unknown;
}
