export type Severity = "high" | "medium" | "low";
export type FormalityLevel = "격식 존댓말" | "중립 존댓말" | "비격식 반말" | "mixed";
export type TargetRewriteLevel = "격식 존댓말" | "중립 존댓말" | "비격식 반말";
export type RewriteSource = "ai" | "rule-based";

export interface DistributionItem {
  label: string;
  count: number;
}

export interface SentenceAnalysis {
  index: number;
  text: string;
  ending: string;
  formality: FormalityLevel;
}

export interface AnalysisIssue {
  type: string;
  severity: Severity;
  message: string;
  sentence_indexes: number[];
  highlight_texts: string[];
}

export interface HighlightSpan {
  text: string;
  type: string;
  severity: Severity;
}

export interface RewriteSuggestion {
  sentence_index: number;
  original_sentence: string;
  current_formality: string;
  target_formality: string;
  reason: string;
  suggested_sentence: string;
  source: RewriteSource;
}

export interface RewritePlanResponse {
  target_level: TargetRewriteLevel;
  dominant_formality: FormalityLevel;
  available_levels: string[];
  summary: string;
  rewrites: RewriteSuggestion[];
}

export interface FullAnalysisResponse {
  overall_score: number;
  formality_level: FormalityLevel;
  formality_score: number;
  consistency_score: number;
  tone_label: string;
  tone_confidence: number;
  sentence_count: number;
  endings_distribution: DistributionItem[];
  sentences: SentenceAnalysis[];
  issues: AnalysisIssue[];
  highlights: HighlightSpan[];
  summary: string;
}

export interface HistoryItem {
  id: number;
  input_text: string;
  overall_score: number;
  formality_level: "격식 존댓말" | "중립 존댓말" | "비격식 반말" | "mixed";
  tone_label: string;
  issue_count: number;
  created_at: string;
  result?: { analysis: FullAnalysisResponse; rewritePlan?: RewritePlanResponse; };
}

export interface StatsResponse {
  total_analyses: number;
  average_score: number;
  most_common_formality: string;
  most_common_tone: string;
}