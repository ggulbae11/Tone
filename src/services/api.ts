import type {
  FullAnalysisResponse,
  HistoryItem,
  RewritePlanResponse,
  StatsResponse,
  TargetRewriteLevel,
} from "../types/analysis";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const REQUEST_TIMEOUT_MS = 15000;

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      headers: {
        "Content-Type": "application/json",
        ...(options?.headers ?? {}),
      },
      ...options,
      signal: controller.signal,
    });

    if (!response.ok) {
      throw new Error(`API request failed: ${response.status}`);
    }

    return response.json() as Promise<T>;
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error("요청 시간이 초과되었습니다. 백엔드 또는 AI 응답을 확인해주세요.");
    }
    throw error;
  } finally {
    window.clearTimeout(timeoutId);
  }
}

export function analyzeText(text: string): Promise<FullAnalysisResponse> {
  return request<FullAnalysisResponse>("/api/analyze/full", {
    method: "POST",
    body: JSON.stringify({ text }),
  });
}

export function fetchRewritePlan(text: string, targetLevel: TargetRewriteLevel): Promise<RewritePlanResponse> {
  return request<RewritePlanResponse>("/api/analyze/rewrite-plan", {
    method: "POST",
    body: JSON.stringify({ text, target_level: targetLevel }),
  });
}

export function fetchHistory(): Promise<HistoryItem[]> {
  return request<HistoryItem[]>("/api/history");
}

export function fetchStats(): Promise<StatsResponse> {
  return request<StatsResponse>("/api/stats");
}