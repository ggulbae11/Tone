import type { ContextFactor } from "../types/analysis";

export interface FactorGroup {
  group: string;
  items: ContextFactor[];
}

/** factors 배열의 group 필드 기준으로 순서를 유지하며 묶어줍니다. */
export function groupFactors(factors: ContextFactor[]): FactorGroup[] {
  const seen = new Map<string, ContextFactor[]>();
  for (const f of factors) {
    const g = f.group || "기타";
    if (!seen.has(g)) seen.set(g, []);
    seen.get(g)!.push(f);
  }
  return Array.from(seen.entries()).map(([group, items]) => ({ group, items }));
}
