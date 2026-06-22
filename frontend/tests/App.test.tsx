import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "../src/App";

vi.mock("react-leaflet", () => ({
  MapContainer: ({ children }: { children: ReactNode }) => (
    <div aria-label="Activity route map" data-testid="route-map">
      {children}
    </div>
  ),
  Polyline: () => <div data-testid="route-line" />,
}));

function renderApp(initialPath = "/") {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialPath]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("App", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn(mockFetch));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders the primary navigation and dashboard data", async () => {
    renderApp();

    for (const label of [
      "Dashboard",
      "Activities",
      "Health",
      "Chat Assistant",
      "Watch Settings",
      "Sync History",
    ]) {
      expect(screen.getByRole("link", { name: label })).toBeInTheDocument();
    }

    expect(screen.getByText("Training overview")).toBeInTheDocument();
    expect(await screen.findByText("Weekly distance")).toBeInTheDocument();
    expect(screen.getAllByText("12.2 km")).toHaveLength(2);
    expect(screen.getByText("Sunday Long Run")).toBeInTheDocument();
  });

  it("filters activities by search text", async () => {
    renderApp("/activities");

    expect(await screen.findByRole("link", { name: "Morning 5K" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Tempo 8K" })).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Search"), {
      target: { value: "tempo" },
    });

    await waitFor(() => {
      expect(screen.queryByRole("link", { name: "Morning 5K" })).not.toBeInTheDocument();
    });
    expect(screen.getByRole("link", { name: "Tempo 8K" })).toBeInTheDocument();
  });

  it("renders activity detail charts, laps, and the route map", async () => {
    renderApp("/activities/seed-activity-001");

    expect(await screen.findByRole("heading", { name: "Morning 5K" })).toBeInTheDocument();
    expect(screen.getByText("5.02 km")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Laps" })).toBeInTheDocument();
    expect(screen.getByTestId("route-map")).toBeInTheDocument();
    expect(screen.getByTestId("route-line")).toBeInTheDocument();
  });

  it("renders a no-map state when samples do not include GPS coordinates", async () => {
    renderApp("/activities/seed-activity-no-gps");

    expect(await screen.findByRole("heading", { name: "Treadmill Recovery" })).toBeInTheDocument();
    expect(screen.getByText("No GPS route")).toBeInTheDocument();
  });

  it("shows health metric availability states", async () => {
    renderApp("/health");

    expect(await screen.findByText("Latest value")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Metric"), {
      target: { value: "body_battery" },
    });

    expect(await screen.findByText("Body Battery unavailable")).toBeInTheDocument();
    expect(
      screen.getByText("This metric has not been imported for the configured watch."),
    ).toBeInTheDocument();
  });

  it("renders failed sync run details", async () => {
    renderApp("/sync-history/seed-sync-002");

    expect(await screen.findByText("Failure detail")).toBeInTheDocument();
    expect(
      screen.getByText("Seeded Bluetooth export unavailable; folder import required."),
    ).toBeInTheDocument();
  });
});

async function mockFetch(input: RequestInfo | URL) {
  const url = new URL(String(input), "http://localhost");

  if (url.pathname === "/api/activities/summary") {
    return jsonResponse(activitySummary(url.searchParams.get("bucket") ?? "week"));
  }

  if (url.pathname === "/api/activities") {
    return jsonResponse({
      items: activities,
      limit: Number(url.searchParams.get("limit") ?? 50),
      offset: Number(url.searchParams.get("offset") ?? 0),
      total: activities.length,
    });
  }

  if (url.pathname === "/api/activities/seed-activity-001") {
    return jsonResponse(activityDetail);
  }

  if (url.pathname === "/api/activities/seed-activity-001/samples") {
    return jsonResponse({
      activity_id: "seed-activity-001",
      samples: gpsSamples,
    });
  }

  if (url.pathname === "/api/activities/seed-activity-no-gps") {
    return jsonResponse(noGpsActivityDetail);
  }

  if (url.pathname === "/api/activities/seed-activity-no-gps/samples") {
    return jsonResponse({
      activity_id: "seed-activity-no-gps",
      samples: noGpsSamples,
    });
  }

  if (url.pathname === "/api/health/metrics") {
    return jsonResponse({
      metrics: [
        {
          first_start_time: "2026-06-01T00:00:00Z",
          last_start_time: "2026-06-15T00:00:00Z",
          metric_type: "steps",
          record_count: 3,
          unit: "count",
        },
        {
          first_start_time: "2026-06-01T00:00:00Z",
          last_start_time: "2026-06-15T00:00:00Z",
          metric_type: "resting_hr",
          record_count: 3,
          unit: "bpm",
        },
      ],
    });
  }

  if (url.pathname === "/api/health/series") {
    const metricType = url.searchParams.get("metric_type");

    if (metricType === "body_battery") {
      return jsonResponse({
        bucket: url.searchParams.get("bucket") ?? "day",
        from_time: null,
        message: "This metric has not been imported for the configured watch.",
        metric_available: false,
        metric_type: "body_battery",
        points: [],
        to_time: null,
        unit: null,
      });
    }

    return jsonResponse({
      bucket: url.searchParams.get("bucket") ?? "day",
      from_time: null,
      message: null,
      metric_available: true,
      metric_type: metricType ?? "steps",
      points: [
        {
          average_value: 8420,
          bucket_end: "2026-06-02T00:00:00Z",
          bucket_start: "2026-06-01T00:00:00Z",
          max_value: 8420,
          min_value: 8420,
          record_count: 1,
          total_value: 8420,
          value: 8420,
        },
        {
          average_value: 9500,
          bucket_end: "2026-06-09T00:00:00Z",
          bucket_start: "2026-06-08T00:00:00Z",
          max_value: 9500,
          min_value: 9500,
          record_count: 1,
          total_value: 9500,
          value: 9500,
        },
      ],
      to_time: null,
      unit: metricType === "resting_hr" ? "bpm" : "count",
    });
  }

  if (url.pathname === "/api/sync-runs") {
    const status = url.searchParams.get("status");
    const items = status ? syncRuns.filter((run) => run.status === status) : syncRuns;

    return jsonResponse({
      items,
      limit: Number(url.searchParams.get("limit") ?? 20),
      offset: Number(url.searchParams.get("offset") ?? 0),
      total: items.length,
    });
  }

  if (url.pathname === "/api/sync-runs/seed-sync-002") {
    return jsonResponse(syncRuns[1]);
  }

  return jsonResponse(
    {
      error: {
        code: "NOT_FOUND",
        message: `Unhandled test URL: ${url.pathname}`,
      },
    },
    404,
  );
}

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    headers: { "Content-Type": "application/json" },
    status,
  });
}

function activitySummary(bucket: string) {
  const buckets =
    bucket === "month"
      ? [
          {
            activity_count: 3,
            avg_heart_rate: 146,
            avg_pace_seconds_per_km: 312,
            bucket_end: "2026-07-01T00:00:00Z",
            bucket_start: "2026-06-01T00:00:00Z",
            distance_meters: 25220,
            duration_seconds: 7890,
            longest_distance_meters: 12160,
          },
        ]
      : [
          {
            activity_count: 1,
            avg_heart_rate: 142,
            avg_pace_seconds_per_km: 308,
            bucket_end: "2026-06-08T00:00:00Z",
            bucket_start: "2026-06-01T00:00:00Z",
            distance_meters: 5020,
            duration_seconds: 1545,
            longest_distance_meters: 5020,
          },
          {
            activity_count: 1,
            avg_heart_rate: 151,
            avg_pace_seconds_per_km: 296,
            bucket_end: "2026-06-15T00:00:00Z",
            bucket_start: "2026-06-08T00:00:00Z",
            distance_meters: 8040,
            duration_seconds: 2380,
            longest_distance_meters: 8040,
          },
          {
            activity_count: 1,
            avg_heart_rate: 146,
            avg_pace_seconds_per_km: 326,
            bucket_end: "2026-06-22T00:00:00Z",
            bucket_start: "2026-06-15T00:00:00Z",
            distance_meters: 12160,
            duration_seconds: 3965,
            longest_distance_meters: 12160,
          },
        ];

  return {
    avg_heart_rate: 146,
    avg_pace_seconds_per_km: 313,
    bucket,
    buckets,
    from_time: null,
    to_time: null,
    total_activities: 3,
    total_distance_meters: 25220,
    total_duration_seconds: 7890,
  };
}

const activities = [
  {
    avg_heart_rate: 146,
    avg_pace_seconds_per_km: 326,
    device_id: "seed-device-forerunner-935",
    distance_meters: 12160,
    duration_seconds: 3965,
    elevation_gain_meters: 86,
    id: "seed-activity-003",
    name: "Sunday Long Run",
    sport: "running",
    started_at: "2026-06-15T06:30:00Z",
  },
  {
    avg_heart_rate: 151,
    avg_pace_seconds_per_km: 296,
    device_id: "seed-device-forerunner-935",
    distance_meters: 8040,
    duration_seconds: 2380,
    elevation_gain_meters: 38,
    id: "seed-activity-002",
    name: "Tempo 8K",
    sport: "running",
    started_at: "2026-06-08T06:30:00Z",
  },
  {
    avg_heart_rate: 142,
    avg_pace_seconds_per_km: 308,
    device_id: "seed-device-forerunner-935",
    distance_meters: 5020,
    duration_seconds: 1545,
    elevation_gain_meters: 24,
    id: "seed-activity-001",
    name: "Morning 5K",
    sport: "running",
    started_at: "2026-06-01T06:30:00Z",
  },
];

const activityDetail = {
  ...activities[2],
  calories: 341,
  max_heart_rate: 164,
  avg_cadence: 166,
  source_activity_id: "garmin-seed-001",
  summary: {
    avg_pace_seconds_per_km: 308,
    avg_speed_meters_per_second: 3.25,
    distance_kilometers: 5.02,
    gps_sample_count: 2,
    has_gps: true,
    lap_count: 2,
    sample_count: 2,
  },
  laps: [
    {
      avg_heart_rate: 142,
      avg_pace_seconds_per_km: 308,
      distance_meters: 1000,
      duration_seconds: 308,
      id: "seed-activity-001-lap-0",
      lap_index: 0,
      started_at: "2026-06-01T06:30:00Z",
    },
    {
      avg_heart_rate: 144,
      avg_pace_seconds_per_km: 308,
      distance_meters: 1000,
      duration_seconds: 308,
      id: "seed-activity-001-lap-1",
      lap_index: 1,
      started_at: "2026-06-01T06:35:00Z",
    },
  ],
  training_effect: 2.4,
};

const noGpsActivityDetail = {
  ...activityDetail,
  distance_meters: 3200,
  id: "seed-activity-no-gps",
  name: "Treadmill Recovery",
  summary: {
    ...activityDetail.summary,
    gps_sample_count: 0,
    has_gps: false,
  },
};

const gpsSamples = [
  {
    cadence: 166,
    distance_meters: 0,
    elapsed_seconds: 0,
    elevation_meters: 42,
    heart_rate: 142,
    id: 1,
    latitude: 47.6205,
    longitude: -122.3493,
    power_watts: 220,
    sample_time: "2026-06-01T06:30:00Z",
    speed_meters_per_second: 3.25,
  },
  {
    cadence: 168,
    distance_meters: 5020,
    elapsed_seconds: 1545,
    elevation_meters: 66,
    heart_rate: 150,
    id: 2,
    latitude: 47.6245,
    longitude: -122.3533,
    power_watts: 235,
    sample_time: "2026-06-01T06:55:45Z",
    speed_meters_per_second: 3.25,
  },
];

const noGpsSamples = gpsSamples.map((sample) => ({
  ...sample,
  latitude: null,
  longitude: null,
}));

const syncRuns = [
  {
    activities_imported: 1,
    device_id: "seed-device-forerunner-935",
    duration_seconds: 180,
    error_summary: null,
    finished_at: "2026-06-15T08:33:00Z",
    health_records_imported: 6,
    id: "seed-sync-003",
    started_at: "2026-06-15T08:30:00Z",
    status: "succeeded",
  },
  {
    activities_imported: 0,
    device_id: "seed-device-forerunner-935",
    duration_seconds: 60,
    error_summary: "Seeded Bluetooth export unavailable; folder import required.",
    finished_at: "2026-06-14T02:01:00Z",
    health_records_imported: 0,
    id: "seed-sync-002",
    started_at: "2026-06-14T02:00:00Z",
    status: "failed",
  },
];
