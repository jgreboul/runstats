import { useQuery } from "@tanstack/react-query";
import type { LatLngExpression } from "leaflet";
import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { MapContainer, Polyline } from "react-leaflet";
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
  getActivity,
  getActivitySamples,
  listActivities,
  queryKeys,
  type ActivityListItem,
  type ActivityListParams,
  type ActivitySample,
} from "../api/runstats";
import {
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
  StatCard,
} from "../components/StatusViews";
import {
  formatDate,
  formatDateTime,
  formatDistance,
  formatDuration,
  formatNumber,
  formatPace,
  formatSport,
  kilometersToMeters,
  speedToPaceMinutes,
  toEndOfDayIso,
  toStartOfDayIso,
} from "../lib/formatters";

interface ActivityFilters {
  fromDate: string;
  maxDistanceKm: string;
  minDistanceKm: string;
  search: string;
  sport: string;
  toDate: string;
}

const defaultFilters: ActivityFilters = {
  fromDate: "",
  maxDistanceKm: "",
  minDistanceKm: "",
  search: "",
  sport: "",
  toDate: "",
};

export function ActivitiesView() {
  const [filters, setFilters] = useState<ActivityFilters>(defaultFilters);
  const activityParams = buildActivityParams(filters);
  const activities = useQuery({
    queryKey: queryKeys.activities.list(activityParams),
    queryFn: () => listActivities(activityParams),
  });

  const filteredActivities = useMemo(() => {
    const searchText = filters.search.trim().toLowerCase();
    const items = activities.data?.items ?? [];

    if (!searchText) {
      return items;
    }

    return items.filter((activity) =>
      `${activity.name} ${activity.sport}`
        .toLowerCase()
        .includes(searchText),
    );
  }, [activities.data?.items, filters.search]);

  return (
    <>
      <PageHeader eyebrow="Activities" title="Activity log" />

      <section className="filter-panel" aria-label="Activity filters">
        <label>
          Search
          <input
            type="search"
            value={filters.search}
            onChange={(event) =>
              setFilters((current) => ({
                ...current,
                search: event.target.value,
              }))
            }
          />
        </label>
        <label>
          From
          <input
            type="date"
            value={filters.fromDate}
            onChange={(event) =>
              setFilters((current) => ({
                ...current,
                fromDate: event.target.value,
              }))
            }
          />
        </label>
        <label>
          To
          <input
            type="date"
            value={filters.toDate}
            onChange={(event) =>
              setFilters((current) => ({
                ...current,
                toDate: event.target.value,
              }))
            }
          />
        </label>
        <label>
          Sport
          <select
            value={filters.sport}
            onChange={(event) =>
              setFilters((current) => ({
                ...current,
                sport: event.target.value,
              }))
            }
          >
            <option value="">All sports</option>
            <option value="running">Running</option>
            <option value="trail_running">Trail Running</option>
            <option value="walking">Walking</option>
            <option value="cycling">Cycling</option>
          </select>
        </label>
        <label>
          Min km
          <input
            min="0"
            step="0.1"
            type="number"
            value={filters.minDistanceKm}
            onChange={(event) =>
              setFilters((current) => ({
                ...current,
                minDistanceKm: event.target.value,
              }))
            }
          />
        </label>
        <label>
          Max km
          <input
            min="0"
            step="0.1"
            type="number"
            value={filters.maxDistanceKm}
            onChange={(event) =>
              setFilters((current) => ({
                ...current,
                maxDistanceKm: event.target.value,
              }))
            }
          />
        </label>
        <button
          className="secondary-button"
          type="button"
          onClick={() => setFilters(defaultFilters)}
        >
          Clear
        </button>
      </section>

      {activities.isLoading ? (
        <LoadingState title="Loading activities" />
      ) : activities.isError ? (
        <ErrorState error={activities.error} title="Activities unavailable" />
      ) : filteredActivities.length === 0 ? (
        <EmptyState
          title="No activities found"
          message="Adjust filters or import activity data."
        />
      ) : (
        <ActivityTable activities={filteredActivities} />
      )}
    </>
  );
}

export function ActivityDetailView() {
  const { activityId = "" } = useParams();
  const activity = useQuery({
    enabled: activityId.length > 0,
    queryKey: queryKeys.activities.detail(activityId),
    queryFn: () => getActivity(activityId),
  });
  const samples = useQuery({
    enabled: activityId.length > 0,
    queryKey: queryKeys.activities.samples(activityId),
    queryFn: () => getActivitySamples(activityId),
  });

  if (activity.isLoading || samples.isLoading) {
    return (
      <>
        <PageHeader eyebrow="Activities" title="Activity detail" />
        <LoadingState title="Loading activity detail" />
      </>
    );
  }

  if (activity.isError) {
    return (
      <>
        <PageHeader eyebrow="Activities" title="Activity detail" />
        <ErrorState error={activity.error} title="Activity unavailable" />
      </>
    );
  }

  if (samples.isError) {
    return (
      <>
        <PageHeader eyebrow="Activities" title="Activity detail" />
        <ErrorState error={samples.error} title="Activity samples unavailable" />
      </>
    );
  }

  if (!activity.data) {
    return (
      <>
        <PageHeader eyebrow="Activities" title="Activity detail" />
        <EmptyState title="Activity not found" />
      </>
    );
  }

  const sampleRows = samples.data?.samples ?? [];
  const routePositions = sampleRows
    .filter(hasCoordinates)
    .map((sample) => [sample.latitude, sample.longitude] as LatLngExpression);

  return (
    <>
      <PageHeader
        eyebrow="Activity detail"
        title={activity.data.name}
        actions={
          <Link className="secondary-button" to="/activities">
            Back to activities
          </Link>
        }
      />

      <section className="stat-grid" aria-label="Activity summary">
        <StatCard label="Distance" value={formatDistance(activity.data.distance_meters)} />
        <StatCard label="Duration" value={formatDuration(activity.data.duration_seconds)} />
        <StatCard label="Pace" value={formatPace(activity.data.avg_pace_seconds_per_km)} />
        <StatCard
          label="Heart rate"
          value={formatNumber(activity.data.avg_heart_rate, " bpm")}
        />
        <StatCard
          label="Elevation"
          value={formatNumber(activity.data.elevation_gain_meters, " m")}
        />
        <StatCard label="Laps" value={String(activity.data.summary.lap_count)} />
      </section>

      <section className="detail-grid">
        <article className="data-panel">
          <div className="panel-heading">
            <h3>Route</h3>
            <p>{formatDateTime(activity.data.started_at)}</p>
          </div>
          <ActivityRouteMap positions={routePositions} />
        </article>

        <article className="data-panel">
          <div className="panel-heading">
            <h3>Activity facts</h3>
            <p>{formatSport(activity.data.sport)}</p>
          </div>
          <dl className="fact-list">
            <div>
              <dt>Calories</dt>
              <dd>{formatNumber(activity.data.calories)}</dd>
            </div>
            <div>
              <dt>Max heart rate</dt>
              <dd>{formatNumber(activity.data.max_heart_rate, " bpm")}</dd>
            </div>
            <div>
              <dt>Cadence</dt>
              <dd>{formatNumber(activity.data.avg_cadence, " spm", 1)}</dd>
            </div>
            <div>
              <dt>Training effect</dt>
              <dd>{formatNumber(activity.data.training_effect, "", 1)}</dd>
            </div>
          </dl>
        </article>
      </section>

      <section className="chart-grid" aria-label="Activity charts">
        <ActivityLineChart
          data={chartRows(sampleRows)}
          dataKey="paceMinutes"
          name="Pace"
          stroke="#1c4d8d"
          title="Pace"
          unit="min/km"
        />
        <ActivityLineChart
          data={chartRows(sampleRows)}
          dataKey="heartRate"
          name="Heart rate"
          stroke="#4988c4"
          title="Heart rate"
          unit="bpm"
        />
        <ActivityLineChart
          data={chartRows(sampleRows)}
          dataKey="elevation"
          name="Elevation"
          stroke="#0f2854"
          title="Elevation"
          unit="m"
        />
        <ActivityLineChart
          data={chartRows(sampleRows)}
          dataKey="cadence"
          name="Cadence"
          stroke="#bde8f5"
          title="Cadence"
          unit="spm"
        />
      </section>

      <section className="data-panel">
        <div className="panel-heading">
          <h3>Laps</h3>
          <p>{activity.data.laps.length} recorded</p>
        </div>
        {activity.data.laps.length > 0 ? (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Lap</th>
                  <th>Started</th>
                  <th>Distance</th>
                  <th>Duration</th>
                  <th>Pace</th>
                  <th>Heart rate</th>
                </tr>
              </thead>
              <tbody>
                {activity.data.laps.map((lap) => (
                  <tr key={lap.id}>
                    <td>{lap.lap_index + 1}</td>
                    <td>{formatDate(lap.started_at)}</td>
                    <td>{formatDistance(lap.distance_meters)}</td>
                    <td>{formatDuration(lap.duration_seconds)}</td>
                    <td>{formatPace(lap.avg_pace_seconds_per_km)}</td>
                    <td>{formatNumber(lap.avg_heart_rate, " bpm")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState title="No lap data" />
        )}
      </section>
    </>
  );
}

function ActivityTable({ activities }: { activities: ActivityListItem[] }) {
  return (
    <section className="data-panel">
      <div className="panel-heading">
        <h3>Activities</h3>
        <p>{activities.length} matching</p>
      </div>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Date</th>
              <th>Name</th>
              <th>Sport</th>
              <th>Distance</th>
              <th>Pace</th>
              <th>Time</th>
              <th>Heart rate</th>
              <th>Elevation</th>
            </tr>
          </thead>
          <tbody>
            {activities.map((activity) => (
              <tr key={activity.id}>
                <td>{formatDate(activity.started_at)}</td>
                <td>
                  <Link to={`/activities/${activity.id}`}>{activity.name}</Link>
                </td>
                <td>{formatSport(activity.sport)}</td>
                <td>{formatDistance(activity.distance_meters)}</td>
                <td>{formatPace(activity.avg_pace_seconds_per_km)}</td>
                <td>{formatDuration(activity.duration_seconds)}</td>
                <td>{formatNumber(activity.avg_heart_rate, " bpm")}</td>
                <td>{formatNumber(activity.elevation_gain_meters, " m")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function ActivityRouteMap({ positions }: { positions: LatLngExpression[] }) {
  if (positions.length === 0) {
    return (
      <EmptyState
        title="No GPS route"
        message="This activity does not include coordinate samples."
      />
    );
  }

  return (
    <div className="map-shell" aria-label="Activity route map">
      <MapContainer
        center={positions[Math.floor(positions.length / 2)]}
        className="route-map"
        scrollWheelZoom={false}
        zoom={14}
      >
        <Polyline pathOptions={{ color: "#1c4d8d", weight: 5 }} positions={positions} />
      </MapContainer>
    </div>
  );
}

function ActivityLineChart({
  data,
  dataKey,
  name,
  stroke,
  title,
  unit,
}: {
  data: ReturnType<typeof chartRows>;
  dataKey: string;
  name: string;
  stroke: string;
  title: string;
  unit: string;
}) {
  return (
    <article className="data-panel">
      <div className="panel-heading">
        <h3>{title}</h3>
        <p>{unit}</p>
      </div>
      {data.length > 0 ? (
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="label" tickLine={false} />
            <YAxis tickLine={false} width={44} />
            <Tooltip />
            <Line
              connectNulls
              dataKey={dataKey}
              name={name}
              stroke={stroke}
              strokeWidth={3}
              type="monotone"
            />
          </LineChart>
        </ResponsiveContainer>
      ) : (
        <EmptyState title={`No ${title.toLowerCase()} samples`} />
      )}
    </article>
  );
}

function buildActivityParams(filters: ActivityFilters): ActivityListParams {
  return {
    from: toStartOfDayIso(filters.fromDate),
    limit: 100,
    max_distance_meters: kilometersToMeters(filters.maxDistanceKm),
    min_distance_meters: kilometersToMeters(filters.minDistanceKm),
    offset: 0,
    sport: filters.sport || null,
    to: toEndOfDayIso(filters.toDate),
  };
}

function chartRows(samples: ActivitySample[]) {
  return samples.map((sample) => ({
    cadence: sample.cadence,
    elevation: sample.elevation_meters,
    heartRate: sample.heart_rate,
    label: `${Math.round(sample.elapsed_seconds / 60)}m`,
    paceMinutes: speedToPaceMinutes(sample.speed_meters_per_second),
  }));
}

function hasCoordinates(
  sample: ActivitySample,
): sample is ActivitySample & { latitude: number; longitude: number } {
  return sample.latitude !== null && sample.longitude !== null;
}
