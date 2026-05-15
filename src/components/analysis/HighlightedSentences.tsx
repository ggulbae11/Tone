import type { HighlightSpan, SentenceAnalysis } from "../../types/analysis";

interface HighlightedSentencesProps {
  sentences: SentenceAnalysis[];
  highlights: HighlightSpan[];
}

function resolveSeverity(text: string, highlights: HighlightSpan[]): string | null {
  const match = highlights.find((highlight) => text.includes(highlight.text));
  return match?.severity ?? null;
}

export function HighlightedSentences({ sentences, highlights }: HighlightedSentencesProps) {
  return (
    <section className="panel">
      <div className="panel__header">
        <h3>문장별 분석</h3>
      </div>
      <div className="sentence-list">
        {sentences.map((sentence) => {
          const severity = resolveSeverity(sentence.text, highlights);
          return (
            <article className={`sentence-item ${severity ? `sentence-item--${severity}` : ""}`} key={sentence.index}>
              <div className="sentence-item__header">
                <span className="badge">{sentence.formality}</span>
                <span>종결어미: {sentence.ending}</span>
              </div>
              <p>{sentence.text}</p>
            </article>
          );
        })}
      </div>
    </section>
  );
}
