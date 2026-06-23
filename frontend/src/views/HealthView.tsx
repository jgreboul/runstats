import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import {
  getHealthSeries,
  listHealthMetrics,
  queryKeys,
  type HealthSeriesBucketName,
} from "../api/runstats";
import {
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
  StatCard,
} from "../components/StatusViews";
import {
  formatNumber,
  formatShortDateUtc,
  formatSport,
  toEndOfDayIso,
  toStartOfDayIso,
} from "../lib/formatters";

const knownMetricOptions = [
  "steps",
  "resting_hr",
  "hrv",
  "sleep",
  "stress",
  "body_battery",
  "respiration",
  "pulse_ox",
];

export function HealthView() {
  const [searchParams] = useSearchParams();
  const requestedMetric = searchParams.get("metric") ?? "steps";
  const [metricType, setMetricType] = useState(requestedMetric);
  const [bucket, setBucket] = useState<HealthSeriesBucketName>("day");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");

  useEffect(() => {
    setMetricType(requestedMetric);
  }, [requestedMetric]);

  const metrics = useQuery({
    queryKey: queryKeys.health.metrics,
    queryFn: listHealthMetrics,
  });
  const seriesParams = useMemo(
    () => ({
      bucket,
      from: toStartOfDayIso(fromDate),
      metric_type: metricType,
      to: toEndOfDayIso(toDate),
    }),
    [bucket, fromDate, metricType, toDate],
  );
  const series = useQuery({
    queryKey: queryKeys.health.series(seriesParams),
    queryFn: () => getHealthSeries(seriesParams),
  });

  const metricOptions = useMemo(() => {
    const discovered = metrics.data?.metrics.map((metric) => metric.metric_type) ?? [];
    return Array.from(new Set([...discovered, ...knownMetricOptions])).sort();
  }, [metrics.data?.metrics]);

  const selectedMetric = metrics.data?.metrics.find(
    (metric) => metric.metric_type === metricType,
  );

  return (
    <>
      <PageHeader eyebrow="Health" title="Health trends" />

      <section className="filter-panel" aria-label="Health filters">
        <label>
          Metric
          <select
            value={metricType}
            onChange={(event) => setMetricType(event.target.value)}
          >
            {metricOptions.map((metric) => (
              <option key={metric} value={metric}>
                {formatMetricName(metric)}
              </option>
            ))}
          </select>
        </label>
        <fieldset className="segmented-control">
          <legend>Bucket</legend>
          {(["day", "week", "month"] as const).map((option) => (
            <label key={option}>
              <input
                checked={bucket === option}
                name="health-bucket"
                type="radio"
                value={option}
                onChange={() => setBucket(option)}
              />
              <span>{formatSport(option)}</span>
            </label>
          ))}
        </fieldset>
        <label>
          From
          <input
            type="date"
            value={fromDate}
            onChange={(event) => setFromDate(event.target.value)}
          />
        </label>
        <label>
          To
          <input
            type="date"
            value={toDate}
            onChange={(event) => setToDate(event.target.value)}
          />
        </label>
      </section>

      {metrics.isLoading || series.isLoading ? (
        <LoadingState title="Loading health metrics" />
      ) : metrics.isError ? (
        <ErrorState error={metrics.error} title="Health metrics unavailable" />
      ) : series.isError ? (
        <ErrorState error={series.error} title="Health series unavailable" />
      ) : series.data?.metric_available === false ? (
        <EmptyState
          title={`${formatMetricName(metricType)} unavailable`}
          message={
            series.data.message ??
            "This metric has not been imported for the configured watch."
          }
        />
      ) : series.data && series.data.points.length > 0 ? (
        <>
          <section className="stat-grid" aria-label="Health metric summary">
            <StatCard
              label="Latest value"
              value={formatHealthValue(
                series.data.points[series.data.points.length - 1]?.value,
                series.data.unit,
              )}
            />
            <StatCard
              label="Average"
              value={formatHealthValue(average(series.data.points), series.data.unit)}
            />
            <StatCard
              label="Records"
              value={String(
                series.data.points.reduce(
                  (total, point) => total + point.record_count,
                  0,
                ),
              )}
            />
            <StatCard
              label="Data range"
              value={
                selectedMetric
                  ? `${formatShortDateUtc(
                      selectedMetric.first_start_time,
                    )} to ${formatShortDateUtc(selectedMetric.last_start_time)}`
                  : "Not available"
              }
            />
          </section>

          <section className="data-panel">
            <div className="panel-heading">
              <h3>{formatMetricName(metricType)}</h3>
              <p>{series.data.bucket} buckets</p>
            </div>
            <ResponsiveContainer width="100%" height={320}>
              <LineChart
                data={series.data.points.map((point) => ({
                  label: formatShortDateUtc(point.bucket_start),
                  value: point.value,
                }))}
              >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="label" tickLine={false} />
                <YAxis tickLine={false} width={56} />
                <Tooltip />
                <Line
                  dataKey="value"
                  name={formatMetricName(metricType)}
                  stroke="#1c4d8d"
                  strokeWidth={3}
                  type="monotone"
                />
              </LineChart>
            </ResponsiveContainer>
          </section>
        </>
      ) : (
        <EmptyState
          title="No health points"
          message="The selected filters did not match any health records."
        />
      )}
    </>
  );
}

function average(points: { value: number }[]): number | null {
  if (points.length === 0) {
    return null;
  }

  return points.reduce((total, point) => total + point.value, 0) / points.length;
}

function formatHealthValue(
  value: number | null | undefined,
  unit: string | null,
): string {
  const precision = unit === "hours" || unit === "ms" ? 1 : 0;
  return formatNumber(value, unit ? ` ${unit}` : "", precision);
}

function formatMetricName(metricType: string): string {
  return formatSport(metricType === "resting_hr" ? "resting heart rate" : metricType);
}
