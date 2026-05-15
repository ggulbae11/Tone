import type { AnalysisIssue } from "../../types/analysis";

interface IssueListProps {
  issues: AnalysisIssue[];
}

export function IssueList({ issues }: IssueListProps) {
  if (!issues.length) {
    return (
      <section className="panel">
        <div className="panel__header">
          <h3>일관성 문제</h3>
        </div>
        <p className="empty-state">감지된 문제가 없습니다.</p>
      </section>
    );
  }

  return (
    <section className="panel">
      <div className="panel__header">
        <h3>일관성 문제</h3>
      </div>
      <div className="issue-list">
        {issues.map((issue, index) => (
          <article className={`issue-item issue-item--${issue.severity}`} key={`${issue.type}-${index}`}>
            <div className="issue-item__meta">
              <span className="badge">{issue.severity}</span>
              <span className="issue-item__type">{issue.type}</span>
            </div>
            <p>{issue.message}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
