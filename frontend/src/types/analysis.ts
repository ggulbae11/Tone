export interface ContextFactor {
  key: string;
  label: string;
  group: string;
  value: string;
  description: string;
}

export interface ImplicitStyle {
  value: string;
  reason: string;
}

export interface ContextAnalysis {
  factors: ContextFactor[];
  overall_summary: string;
  implicit_style: ImplicitStyle | null;
}

export interface SentenceResult {
  index: number;
  text: string;
  // 1차: 개별 요소 대조
  is_consistent: boolean;
  violated_factors: string[];
  inconsistency_reason: string | null;
  suggested_rewrite: string | null;
  // 2차: 전체 흐름 대조
  has_flow_issue: boolean;
  flow_issue_reason: string | null;
  flow_suggested_rewrite: string | null;
  // 3차: 암묵적 문체 이탈
  has_implicit_style_issue: boolean;
  implicit_style_reason: string | null;
  implicit_style_rewrite: string | null;
}

export interface ContextOnlyResponse {
  context: ContextAnalysis;
}

export interface FullAnalysisResponse {
  context: ContextAnalysis;
  sentences: SentenceResult[];
  overall_score: number;
  consistent_count: number;
  inconsistent_count: number;
  flow_issue_count: number;
  implicit_style_issue_count: number;
  flow_summary: string;
  summary: string;
}

export interface HistoryItem {
  id: number;
  input_text: string;
  overall_score: number;
  formality_level: string;
  tone_label: string;
  issue_count: number;
  result_payload: FullAnalysisResponse;
  created_at: string;
}

export interface StatsResponse {
  total_analyses: number;
  average_score: number;
  most_common_formality: string;
  most_common_tone: string;
}
