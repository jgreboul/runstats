import { useQuery } from "@tanstack/react-query";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import {
  getActivitySummary,
  getHealthSeries,
  listActivities,
  listSyncRuns,
  queryKeys,
  type ActivitySummaryBucket,
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
  formatDistance,
  formatDuration,
  formatPace,
  formatShortDateUtc,
  formatStatus,
  secondsPerKilometerToMinutes,
} from "../lib/formatters";

export function DashboardView() {
  const weeklySummary = useQuery({
    queryKey: queryKeys.activities.summary({ bucket: "week" }),
    queryFn: () => getActivitySummary({ bucket: "week" }),
  });
  const monthlySummary = useQuery({
    queryKey: queryKeys.activities.summary({ bucket: "month" }),
    queryFn: () => getActivitySummary({ bucket: "month" }),
  });
  const recentActivities = useQuery({
    queryKey: queryKeys.activities.list({ limit: 5 }),
    queryFn: () => listActivities({ limit: 5 }),
  });
  const stepsTrend = useQuery({
    queryKey: queryKeys.health.series({ metric_type: "steps", bucket: "day" }),
    queryFn: () => getHealthSeries({ metric_type: "steps", bucket: "day" }),
  });
  const lastSync = useQuery({
    queryKey: queryKeys.syncRuns.list({ limit: 1 }),
    queryFn: () => listSyncRuns({ limit: 1 }),
  });

  const queries = [
    weeklySummary,
    monthlySummary,
    recentActivities,
    stepsTrend,
    lastSync,
  ];
  const failedQuery = queries.find((query) => query.isError);

  if (queries.some((query) => query.isLoading)) {
    return (
      <>
        <PageHeader eyebrow="Dashboard" title="Training overview" />
        <LoadingState title="Loading dashboard" />
      </>
    );
  }

  if (failedQuery?.error) {
    return (
      <>
        <PageHeader eyebrow="Dashboard" title="Training overview" />
        <ErrorState error={failedQuery.error} title="Dashboard unavailable" />
      </>
    );
  }

  const weeklyBucket = latestBucket(weeklySummary.data?.buckets ?? []);
  const monthlyBucket = latestBucket(monthlySummary.data?.buckets ?? []);
  const currentSync = lastSync.data?.items[0] ?? null;
  const hasActivityData = (weeklySummary.data?.total_activities ?? 0) > 0;
  const hasHealthData = (stepsTrend.data?.points.length ?? 0) > 0;

  return (
    <>
      <PageHeader eyebrow="Dashboard" title="Training overview" />

      {!hasActivityData && !hasHealthData ? (
        <EmptyState
          title="No dashboard data yet"
          message="Seed or import activities and health metrics to populate this view."
        />
      ) : (
        <>
          <section className="stat-grid" aria-label="Dashboard summary">
            <StatCard
              label="Weekly distance"
              value={formatDistance(weeklyBucket?.distance_meters ?? null)}
            />
            <StatCard
              label="Monthly distance"
              value={formatDistance(monthlyBucket?.distance_meters ?? null)}
            />
            <StatCard
              label="Average pace"
              value={formatPace(weeklySummary.data?.avg_pace_seconds_per_km)}
            />
            <StatCard
              label="Last sync"
              tone={syncTone(currentSync?.status)}
              value={
                currentSync
                  ? `${formatStatus(currentSync.status)} - ${formatDateTime(
                      currentSync.started_at,
                    )}`
                  : "Not available"
              }
            />
          </section>

          <section className="dashboard-grid">
            <article className="data-panel">
              <div className="panel-heading">
                <h3>Pace trend</h3>
                <p>Minutes per kilometer by week</p>
              </div>
              {hasActivityData ? (
                <ResponsiveContainer width="100%" height={240}>
                  <LineChart data={runningTrendData(weeklySummary.data?.buckets ?? [])}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="label" tickLine={false} />
                    <YAxis tickLine={false} width={44} />
                    <Tooltip />
                    <Line
                      dataKey="paceMinutes"
                      name="Pace"
                      stroke="#1c4d8d"
                      strokeWidth={3}
                      type="monotone"
                    />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <EmptyState title="No pace data" />
              )}
            </article>

            <article className="data-panel">
              <div className="panel-heading">
                <h3>Heart-rate trend</h3>
                <p>Average beats per minute by week</p>
              </div>
              {hasActivityData ? (
                <ResponsiveContainer width="100%" height={240}>
                  <LineChart data={runningTrendData(weeklySummary.data?.buckets ?? [])}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="label" tickLine={false} />
                    <YAxis tickLine={false} width={44} />
                    <Tooltip />
                    <Line
                      dataKey="heartRate"
                      name="Heart rate"
                      stroke="#4988c4"
                      strokeWidth={3}
                      type="monotone"
                    />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <EmptyState title="No heart-rate data" />
              )}
            </article>

            <article className="data-panel">
              <div className="panel-heading">
                <h3>Steps trend</h3>
                <p>Daily totals from available health data</p>
              </div>
              {hasHealthData ? (
                <ResponsiveContainer width="100%" height={240}>
                  <BarChart
                    data={(stepsTrend.data?.points ?? []).map((point) => ({
                      label: formatShortDateUtc(point.bucket_start),
                      steps: point.value,
                    }))}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="label" tickLine={false} />
                    <YAxis tickLine={false} width={54} />
                    <Tooltip />
                    <Bar dataKey="steps" fill="#4988c4" name="Steps" radius={4} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <EmptyState title="No steps data" />
              )}
            </article>

            <article className="data-panel">
              <div className="panel-heading">
                <h3>Recent activities</h3>
                <p>Latest runs from the local database</p>
              </div>
              {(recentActivities.data?.items.length ?? 0) > 0 ? (
                <div className="activity-stack">
                  {recentActivities.data?.items.map((activity) => (
                    <div className="activity-row" key={activity.id}>
                      <div>
                        <strong>{activity.name}</strong>
                        <span>{formatDateTime(activity.started_at)}</span>
                      </div>
                      <div className="activity-row-metrics">
                        <span>{formatDistance(activity.distance_meters)}</span>
                        <span>{formatDuration(activity.duration_seconds)}</span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <EmptyState title="No recent activities" />
              )}
            </article>
          </section>
        </>
      )}
    </>
  );
}

function latestBucket(
  buckets: ActivitySummaryBucket[],
): ActivitySummaryBucket | null {
  return buckets.length > 0 ? buckets[buckets.length - 1] : null;
}

function runningTrendData(buckets: ActivitySummaryBucket[]) {
  return buckets.map((bucket) => ({
    heartRate: bucket.avg_heart_rate,
    label: formatShortDateUtc(bucket.bucket_start),
    paceMinutes: secondsPerKilometerToMinutes(bucket.avg_pace_seconds_per_km),
  }));
}

function syncTone(status: string | null | undefined) {
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
