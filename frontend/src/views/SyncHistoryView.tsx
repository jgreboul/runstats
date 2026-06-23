import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import {
  getSyncRun,
  listSyncRuns,
  queryKeys,
  retrySyncRun,
  type SyncRun,
} from "../api/runstats";
import {
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
  StatCard,
} from "../components/StatusViews";
import {
  formatDateTime,
  formatDuration,
  formatNumber,
  formatStatus,
} from "../lib/formatters";

export function SyncHistoryView() {
  const [status, setStatus] = useState("");
  const syncRuns = useQuery({
    queryKey: queryKeys.syncRuns.list({ limit: 100, status: status || null }),
    queryFn: () => listSyncRuns({ limit: 100, status: status || null }),
  });

  return (
    <>
      <PageHeader eyebrow="Sync History" title="Sync runs" />

      <section className="filter-panel" aria-label="Sync filters">
        <label>
          Status
          <select value={status} onChange={(event) => setStatus(event.target.value)}>
            <option value="">All statuses</option>
            <option value="running">Running</option>
            <option value="succeeded">Succeeded</option>
            <option value="failed">Failed</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </label>
      </section>

      {syncRuns.isLoading ? (
        <LoadingState title="Loading sync history" />
      ) : syncRuns.isError ? (
        <ErrorState error={syncRuns.error} title="Sync history unavailable" />
      ) : (syncRuns.data?.items.length ?? 0) === 0 ? (
        <EmptyState title="No sync runs" message="Sync attempts will appear here." />
      ) : (
        <section className="data-panel">
          <div className="panel-heading">
            <h3>Runs</h3>
            <p>{syncRuns.data?.total ?? 0} total</p>
          </div>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Status</th>
                  <th>Started</th>
                  <th>Duration</th>
                  <th>Activities</th>
                  <th>Health records</th>
                  <th>Error code</th>
                  <th>Error</th>
                </tr>
              </thead>
              <tbody>
                {syncRuns.data?.items.map((run) => (
                  <tr key={run.id}>
                    <td>
                      <Link
                        className={`status-pill status-${run.status}`}
                        to={`/sync-history/${run.id}`}
                      >
                        {formatStatus(run.status)}
                      </Link>
                    </td>
                    <td>{formatDateTime(run.started_at)}</td>
                    <td>{formatDuration(run.duration_seconds)}</td>
                    <td>{run.activities_imported}</td>
                    <td>{run.health_records_imported}</td>
                    <td>{run.error_code ?? "None"}</td>
                    <td>{run.error_summary ?? "None"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </>
  );
}

export function SyncRunDetailView() {
  const { syncRunId = "" } = useParams();
  const queryClient = useQueryClient();
  const [retriedRun, setRetriedRun] = useState<SyncRun | null>(null);
  const syncRun = useQuery({
    enabled: syncRunId.length > 0,
    queryKey: queryKeys.syncRuns.detail(syncRunId),
    queryFn: () => getSyncRun(syncRunId),
  });
  const retryMutation = useMutation({
    mutationFn: () => retrySyncRun(syncRunId),
    onSuccess: (run) => {
      setRetriedRun(run);
      void queryClient.invalidateQueries({ queryKey: queryKeys.syncRuns.all });
    },
  });

  if (syncRun.isLoading) {
    return (
      <>
        <PageHeader eyebrow="Sync History" title="Sync run detail" />
        <LoadingState title="Loading sync run" />
      </>
    );
  }

  if (syncRun.isError) {
    return (
      <>
        <PageHeader eyebrow="Sync History" title="Sync run detail" />
        <ErrorState error={syncRun.error} title="Sync run unavailable" />
      </>
    );
  }

  if (!syncRun.data) {
    return (
      <>
        <PageHeader eyebrow="Sync History" title="Sync run detail" />
        <EmptyState title="Sync run not found" />
      </>
    );
  }

  return (
    <>
      <PageHeader
        eyebrow="Sync run detail"
        title={formatStatus(syncRun.data.status)}
        actions={
          <>
            {syncRun.data.status === "failed" ? (
              <button
                className="secondary-button"
                disabled={retryMutation.isPending}
                onClick={() => retryMutation.mutate()}
                type="button"
              >
                {retryMutation.isPending ? "Retrying..." : "Retry sync"}
              </button>
            ) : null}
            <Link className="secondary-button" to="/sync-history">
              Back to sync history
            </Link>
          </>
        }
      />

      <section className="stat-grid" aria-label="Sync run summary">
        <StatCard
          label="Status"
          tone={syncTone(syncRun.data.status)}
          value={formatStatus(syncRun.data.status)}
        />
        <StatCard label="Started" value={formatDateTime(syncRun.data.started_at)} />
        <StatCard label="Duration" value={formatDuration(syncRun.data.duration_seconds)} />
        <StatCard
          label="Imported"
          value={`${formatNumber(syncRun.data.activities_imported)} activities`}
        />
        <StatCard
          label="Health records"
          value={formatNumber(syncRun.data.health_records_imported)}
        />
        <StatCard label="Error code" value={syncRun.data.error_code ?? "None"} />
      </section>

      {retriedRun ? (
        <section className="state-panel" aria-live="polite">
          <div>
            <h3>Retry started</h3>
            <p>
              <Link to={`/sync-history/${retriedRun.id}`}>
                {formatStatus(retriedRun.status)} retry
              </Link>
            </p>
          </div>
        </section>
      ) : null}

      {retryMutation.isError ? (
        <ErrorState error={retryMutation.error} title="Retry failed" />
      ) : null}

      <section className="data-panel">
        <div className="panel-heading">
          <h3>Run notes</h3>
          <p>{syncRun.data.id}</p>
        </div>
        {syncRun.data.error_summary ? (
          <div className="error-callout">
            <strong>Failure detail</strong>
            <p>{syncRun.data.error_summary}</p>
          </div>
        ) : (
          <EmptyState title="No errors recorded" />
        )}
      </section>
    </>
  );
}

function syncTone(status: string) {
  if (status === "succeeded") {
    return "good";
  }

  if (status === "failed") {
    return "bad";
  }

  if (status === "running") {
    return "warn";
  }

  return "default";
}
