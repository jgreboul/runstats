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
    resetChatState();
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
      "Data Management",
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

    expect(await screen.findByText("WATCH_EXPORT_FAILED")).toBeInTheDocument();
    expect(await screen.findByText("Failure detail")).toBeInTheDocument();
    expect(
      screen.getByText("Seeded Bluetooth export unavailable; folder import required."),
    ).toBeInTheDocument();
  });

  it("retries failed sync runs from sync history", async () => {
    renderApp("/sync-history/seed-sync-002");

    fireEvent.click(await screen.findByRole("button", { name: "Retry sync" }));

    expect(await screen.findByText("Retry started")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Succeeded retry" })).toHaveAttribute(
      "href",
      "/sync-history/retry-sync-004",
    );
  });

  it("renders chat history and sends a grounded question", async () => {
    renderApp("/chat");

    expect(await screen.findByText("Seed training questions")).toBeInTheDocument();
    expect(screen.getByText("The seeded data contains 25.22 km.")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Message"), {
      target: { value: "Show my longest run with heart-rate details." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));

    expect(await screen.findAllByText("Longest run: Sunday Long Run.")).toHaveLength(2);
    expect(screen.getByRole("link", { name: "Sunday Long Run" })).toHaveAttribute(
      "href",
      "/activities/seed-activity-003",
    );
  });

  it("exports data and confirms destructive data-management actions", async () => {
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    renderApp("/data-management");

    expect(await screen.findByText("Data export")).toBeInTheDocument();

    fireEvent.click(screen.getByLabelText("Include raw archived files"));
    fireEvent.click(screen.getByRole("button", { name: "Export JSON" }));

    expect(await screen.findByText("Export ready")).toBeInTheDocument();
    expect(lastExportRequest).toEqual({
      include_chat_history: false,
      include_raw_files: true,
    });
    expect(screen.getByText("Health records")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Delete chat history" }));
    expect(await screen.findByText("Deleted 2 chat messages.")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Type device name to confirm"), {
      target: { value: "Garmin Forerunner 935" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Delete imported data" }));

    expect(
      await screen.findByText(
        "Deleted 3 activities, 12 health records, and 3 raw import records.",
      ),
    ).toBeInTheDocument();
    expect(confirmSpy).toHaveBeenCalledTimes(2);
  });
});

async function mockFetch(input: RequestInfo | URL, init?: RequestInit) {
  const url = new URL(String(input), "http://localhost");

  if (url.pathname === "/api/devices") {
    return jsonResponse({ items: [mockDevice] });
  }

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

  if (url.pathname === "/api/sync-runs/seed-sync-002/retry") {
    return jsonResponse(
      {
        activities_imported: 0,
        device_id: "seed-device-forerunner-935",
        duration_seconds: 45,
        error_code: null,
        error_summary: null,
        finished_at: "2026-06-15T09:00:45Z",
        health_records_imported: 2,
        id: "retry-sync-004",
        started_at: "2026-06-15T09:00:00Z",
        status: "succeeded",
      },
      201,
    );
  }

  if (url.pathname === "/api/chat/sessions" && init?.method === "POST") {
    const session = {
      created_at: "2026-06-15T12:00:00Z",
      id: "created-chat-session",
      messages: [],
      title: "New chat",
      updated_at: "2026-06-15T12:00:00Z",
    };
    chatSessions = [sessionListItem(session), ...chatSessions];
    chatMessagesBySession.set(session.id, []);
    return jsonResponse(session);
  }

  if (url.pathname === "/api/chat/sessions" && init?.method === "DELETE") {
    chatSessions = [];
    chatMessagesBySession.clear();
    return new Response(null, { status: 204 });
  }

  if (url.pathname === "/api/chat/sessions") {
    return jsonResponse({
      items: chatSessions,
      limit: Number(url.searchParams.get("limit") ?? 20),
      offset: Number(url.searchParams.get("offset") ?? 0),
      total: chatSessions.length,
    });
  }

  if (url.pathname === "/api/data-management/export" && init?.method === "POST") {
    lastExportRequest = JSON.parse(String(init.body ?? "{}")) as Record<
      string,
      boolean
    >;
    return jsonResponse({
      activities,
      chat_sessions: [],
      counts: {
        activities: 3,
        activity_laps: 19,
        activity_samples: 18,
        chat_messages: 0,
        chat_sessions: 0,
        devices: 1,
        health_metrics: 12,
        raw_files: lastExportRequest.include_raw_files ? 3 : 0,
        raw_imports: 3,
      },
      devices: [mockDevice],
      exported_at: "2026-06-22T12:00:00Z",
      format_version: "runstats.local-data.v1",
      health_metrics: [],
      include_chat_history: lastExportRequest.include_chat_history,
      include_raw_files: lastExportRequest.include_raw_files,
      raw_files: [],
      raw_imports: [],
    });
  }

  if (
    url.pathname === "/api/data-management/chat-history" &&
    init?.method === "DELETE"
  ) {
    return jsonResponse(deletionResponse({ deleted_chat_messages: 2 }));
  }

  if (
    url.pathname ===
      "/api/data-management/devices/seed-device-forerunner-935/imported-data" &&
    init?.method === "DELETE"
  ) {
    return jsonResponse(
      deletionResponse({
        deleted_activities: 3,
        deleted_health_metrics: 12,
        deleted_raw_imports: 3,
      }),
    );
  }

  const chatMessageMatch = url.pathname.match(
    /^\/api\/chat\/sessions\/([^/]+)\/messages$/,
  );
  if (chatMessageMatch && init?.method === "POST") {
    const sessionId = chatMessageMatch[1];
    const body = JSON.parse(String(init?.body)) as { message: string };
    const messages = chatMessagesBySession.get(sessionId) ?? [];
    messages.push({
      content: body.message,
      created_at: "2026-06-15T12:01:00Z",
      id: "chat-user-new",
      role: "user",
      session_id: sessionId,
      tool_trace: null,
    });
    messages.push({
      content: "Longest run: Sunday Long Run.",
      created_at: "2026-06-15T12:01:10Z",
      id: "chat-assistant-new",
      role: "assistant",
      session_id: sessionId,
      tool_trace: chatSupportingData,
    });
    chatMessagesBySession.set(sessionId, messages);
    chatSessions = chatSessions.map((session) =>
      session.id === sessionId
        ? {
            ...session,
            last_message_preview: "Longest run: Sunday Long Run.",
            message_count: messages.length,
            updated_at: "2026-06-15T12:01:10Z",
          }
        : session,
    );
    return jsonResponse({
      answer: "Longest run: Sunday Long Run.",
      message_id: "chat-assistant-new",
      supporting_data: chatSupportingData,
    });
  }

  const chatSessionMatch = url.pathname.match(/^\/api\/chat\/sessions\/([^/]+)$/);
  if (chatSessionMatch) {
    const sessionId = chatSessionMatch[1];
    const session = chatSessions.find((item) => item.id === sessionId);
    if (!session) {
      return jsonResponse({ error: { code: "CHAT_SESSION_NOT_FOUND" } }, 404);
    }
    return jsonResponse({
      created_at: session.created_at,
      id: session.id,
      messages: chatMessagesBySession.get(session.id) ?? [],
      title: session.title,
      updated_at: session.updated_at,
    });
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
    error_code: null,
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
    error_code: "WATCH_EXPORT_FAILED",
    error_summary: "Seeded Bluetooth export unavailable; folder import required.",
    finished_at: "2026-06-14T02:01:00Z",
    health_records_imported: 0,
    id: "seed-sync-002",
    started_at: "2026-06-14T02:00:00Z",
    status: "failed",
  },
];

let chatSessions: ReturnType<typeof sessionListItem>[] = [];
let chatMessagesBySession = new Map<string, unknown[]>();
let lastExportRequest: Record<string, boolean> | null = null;

const mockDevice = {
  bluetooth_address: "seed-ble-forerunner-935",
  capabilities: {
    capability_notes: "Use folder import until direct export is verified.",
    device_id: "seed-device-forerunner-935",
    probed_at: "2026-06-13T06:30:00Z",
    supports_ble_activity_export: false,
    supports_ble_health_export: false,
    supports_folder_import: true,
  },
  created_at: "2026-05-22T06:30:00Z",
  firmware_version: "21.00",
  id: "seed-device-forerunner-935",
  last_seen_at: "2026-06-15T07:30:00Z",
  model: "Forerunner 935",
  name: "Garmin Forerunner 935",
  paired_at: "2026-05-22T06:30:00Z",
  serial_number: "FR935-SEED-001",
  settings: {
    auto_sync_enabled: true,
    device_id: "seed-device-forerunner-935",
    historical_fit_import_folder: null,
    import_activities: true,
    import_health_stats: true,
    preferred_units: "metric",
    sync_interval_minutes: 180,
  },
  updated_at: "2026-06-15T07:30:00Z",
};

const chatSupportingData = {
  intent: "combined",
  metrics: ["running_distance", "heart_rate"],
  notes: [],
  references: [
    {
      href: "/activities/seed-activity-003",
      id: "seed-activity-003",
      label: "Sunday Long Run",
      type: "activity",
    },
  ],
  row_count: 2,
  time_range: "2026-06-15 to 2026-06-15",
  tool_names: ["longest_run", "activity_detail_lookup"],
};

function resetChatState() {
  lastExportRequest = null;
  const seedSession = {
    created_at: "2026-06-15T10:00:00Z",
    id: "seed-chat-session",
    messages: [
      {
        content: "How much did I run in the seeded data?",
        created_at: "2026-06-15T10:00:00Z",
        id: "chat-user-1",
        role: "user",
        session_id: "seed-chat-session",
        tool_trace: null,
      },
      {
        content: "The seeded data contains 25.22 km.",
        created_at: "2026-06-15T10:01:00Z",
        id: "chat-assistant-1",
        role: "assistant",
        session_id: "seed-chat-session",
        tool_trace: {
          intent: "weekly_running_summary",
          metrics: ["running_distance"],
          notes: [],
          references: [],
          row_count: 3,
          time_range: null,
          tool_names: ["weekly_running_summary"],
        },
      },
    ],
    title: "Seed training questions",
    updated_at: "2026-06-15T10:01:00Z",
  };
  chatSessions = [sessionListItem(seedSession)];
  chatMessagesBySession = new Map([[seedSession.id, seedSession.messages]]);
}

function deletionResponse(overrides: Record<string, number>) {
  return {
    deleted_activities: 0,
    deleted_activity_laps: 0,
    deleted_activity_samples: 0,
    deleted_chat_messages: 0,
    deleted_chat_sessions: 0,
    deleted_health_metrics: 0,
    deleted_raw_files: 0,
    deleted_raw_imports: 0,
    device_id: null,
    missing_raw_files: 0,
    ...overrides,
  };
}

function sessionListItem(session: {
  created_at: string;
  id: string;
  messages: unknown[];
  title: string;
  updated_at: string;
}) {
  const lastMessage = session.messages[session.messages.length - 1] as
    | { content?: string }
    | undefined;
  return {
    created_at: session.created_at,
    id: session.id,
    last_message_preview: lastMessage?.content ?? null,
    message_count: session.messages.length,
    title: session.title,
    updated_at: session.updated_at,
  };
}
