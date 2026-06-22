import type { ReactNode } from "react";

import { ApiError } from "../api/runstats";

interface PageHeaderProps {
  actions?: ReactNode;
  eyebrow: string;
  title: string;
}

interface StateProps {
  message?: string;
  title: string;
}

interface StatCardProps {
  label: string;
  tone?: "default" | "good" | "warn" | "bad";
  value: string;
}

export function PageHeader({ actions, eyebrow, title }: PageHeaderProps) {
  return (
    <header className="page-header">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h2>{title}</h2>
      </div>
      {actions ? <div className="page-actions">{actions}</div> : null}
    </header>
  );
}

export function LoadingState({ message = "Loading data", title }: StateProps) {
  return (
    <section className="state-panel" aria-live="polite">
      <div className="loading-mark" aria-hidden="true" />
      <div>
        <h3>{title}</h3>
        <p>{message}</p>
      </div>
    </section>
  );
}

export function EmptyState({ message, title }: StateProps) {
  return (
    <section className="state-panel state-panel-empty">
      <div>
        <h3>{title}</h3>
        {message ? <p>{message}</p> : null}
      </div>
    </section>
  );
}

export function ErrorState({ error, title }: { error: unknown; title: string }) {
  return (
    <section className="state-panel state-panel-error" role="alert">
      <div>
        <h3>{title}</h3>
        <p>{errorMessage(error)}</p>
      </div>
    </section>
  );
}

export function StatCard({ label, tone = "default", value }: StatCardProps) {
  return (
    <article className={`stat-card stat-card-${tone}`}>
      <p>{label}</p>
      <strong>{value}</strong>
    </article>
  );
}

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "RunStats could not load this data.";
}
