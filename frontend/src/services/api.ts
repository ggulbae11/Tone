import type { ContextOnlyResponse, FullAnalysisResponse, HistoryItem, StatsResponse } from "../types/analysis";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const REQUEST_TIMEOUT_MS = 30000;

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      headers: { "Content-Type": "application/json", ...(options?.headers ?? {}) },
      ...options,
      signal: controller.signal,
    });
    if (!response.ok) {
      let detail = "";
      try {
        const body = await response.json() as { detail?: string };
        if (body.detail) detail = ` — ${body.detail}`;
      } catch { /* ignore */ }
      throw new Error(`서버 오류 (${response.status})${detail}`);
    }
    return response.json() as Promise<T>;
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error("요청 시간이 초과되었습니다.");
    }
    throw error;
  } finally {
    window.clearTimeout(timeoutId);
  }
}

/** 1단계: 맥락 추출 */
export function extractContext(text: string): Promise<ContextOnlyResponse> {
  return request<ContextOnlyResponse>("/api/analyze/context", {
    method: "POST",
    body: JSON.stringify({ text }),
  });
}

/** 2단계: 확정된 맥락으로 문장 분석 */
export function analyzeSentences(
  text: string,
  contextValues: Record<string, string>,
  overallSummary: string,
  implicitStyleValue: string = "",
): Promise<FullAnalysisResponse> {
  return request<FullAnalysisResponse>("/api/analyze/sentences", {
    method: "POST",
    body: JSON.stringify({
      text,
      context_values: contextValues,
      overall_summary: overallSummary,
      implicit_style_value: implicitStyleValue,
    }),
  });
}

export function fetchHistory(): Promise<HistoryItem[]> {
  return request<HistoryItem[]>("/api/history");
}

export function fetchStats(): Promise<StatsResponse> {
  return request<StatsResponse>("/api/stats");
}

export function clearHistory(): Promise<{ deleted: boolean }> {
  return request<{ deleted: boolean }>("/api/history", { method: "DELETE" });
}
