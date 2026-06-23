import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type {
  Device,
  DeviceSettingsPatchRequest,
  SyncProgressEvent,
} from "../src/api/runstats";
import { WatchSettingsView } from "../src/views/WatchSettingsView";

function renderWatchSettings() {
  const queryClient = new QueryClient({
    defaultOptions: {
      mutations: { retry: false },
      queries: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <WatchSettingsView />
    </QueryClientProvider>,
  );
}

describe("WatchSettingsView", () => {
  beforeEach(() => {
    devices = [];
    fitImportRequest = null;
    fitImportResponse = {
      created: 1,
      failed: 0,
      files: [],
      raw_files_archived: 1,
      skipped: 1,
    };
    scanFails = false;
    settingsPatch = null;
    MockWebSocket.instances = [];
    vi.stubGlobal("fetch", vi.fn(mockFetch));
    vi.stubGlobal("WebSocket", MockWebSocket);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("scans and pairs a discovered Forerunner watch", async () => {
    renderWatchSettings();

    expect(await screen.findByText("No watch configured")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Scan" }));
    const pairButton = await screen.findByRole("button", {
      name: /^Pair Garmin Forerunner 935$/,
    });
    fireEvent.click(pairButton);

    await waitFor(() => {
      expect(screen.getByText("Forerunner 935")).toBeInTheDocument();
    });
    expect(screen.getByText("Folder import")).toBeInTheDocument();
    expect(screen.getAllByText("Supported").length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole("button", { name: "Probe capabilities" }));

    expect(
      await screen.findByText("Direct activity export detected."),
    ).toBeInTheDocument();
    expect(screen.getAllByText("Supported").length).toBeGreaterThan(1);
  });

  it("saves settings, tests connection, and streams manual sync", async () => {
    devices = [mockDevice()];
    renderWatchSettings();

    expect(await screen.findByRole("button", { name: "Test connection" }))
      .toBeInTheDocument();

    fireEvent.click(screen.getByLabelText("Automatic sync"));
    fireEvent.change(screen.getByLabelText("Preferred units"), {
      target: { value: "imperial" },
    });
    fireEvent.change(screen.getByLabelText("Historical FIT import folder"), {
      target: { value: "D:/Runs/FIT" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save settings" }));

    expect(await screen.findByText("Settings saved.")).toBeInTheDocument();
    expect(settingsPatch).toMatchObject({
      auto_sync_enabled: true,
      historical_fit_import_folder: "D:/Runs/FIT",
      preferred_units: "imperial",
    });

    fireEvent.click(screen.getByRole("button", { name: "Test connection" }));
    expect(await screen.findByText("Connected")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Start sync" }));
    expect(await screen.findByText("Sync succeeded")).toBeInTheDocument();
    expect(screen.getByText("Sync completed successfully.")).toBeInTheDocument();
    expect(MockWebSocket.instances[0]?.url).toContain(
      "/api/sync-runs/mock-sync-001/events",
    );

    fireEvent.click(screen.getByRole("button", { name: "Import FIT folder" }));
    expect(await screen.findByText(/1 imported, 1 skipped, 0 failed/))
      .toBeInTheDocument();
    expect(fitImportRequest).toMatchObject({
      device_id: "mock-device-1",
      folder_path: "D:/Runs/FIT",
      recursive: true,
    });
  });

  it("prompts for a folder path before importing FIT files", async () => {
    devices = [mockDevice()];
    renderWatchSettings();

    fireEvent.click(await screen.findByRole("button", { name: "Import FIT folder" }));

    expect(await screen.findByText("FIT import failed")).toBeInTheDocument();
    expect(
      screen.getByText("Choose a historical FIT import folder first."),
    ).toBeInTheDocument();
    expect(fitImportRequest).toBeNull();
  });

  it("explains when the selected FIT folder contains no FIT files", async () => {
    const device = mockDevice();
    devices = [
      {
        ...device,
        settings: {
          ...device.settings,
          historical_fit_import_folder: "D:/Runs/Empty",
        },
      },
    ];
    fitImportResponse = {
      created: 0,
      failed: 0,
      files: [],
      raw_files_archived: 0,
      skipped: 0,
    };
    renderWatchSettings();

    await screen.findByDisplayValue("D:/Runs/Empty");
    fireEvent.click(await screen.findByRole("button", { name: "Import FIT folder" }));

    expect(await screen.findByText("No FIT files found")).toBeInTheDocument();
    expect(
      screen.getByText(/found no files ending in .fit/i),
    ).toBeInTheDocument();
  });

  it("shows Bluetooth unavailable scan errors", async () => {
    scanFails = true;
    renderWatchSettings();

    fireEvent.click(await screen.findByRole("button", { name: "Scan" }));

    expect(await screen.findByText("Bluetooth unavailable")).toBeInTheDocument();
    expect(screen.getByText("Bluetooth adapter is unavailable.")).toBeInTheDocument();
  });
});

let devices: Device[] = [];
let fitImportRequest: unknown = null;
let fitImportResponse = {
  created: 1,
  failed: 0,
  files: [],
  raw_files_archived: 1,
  skipped: 1,
};
let scanFails = false;
let settingsPatch: DeviceSettingsPatchRequest | null = null;

async function mockFetch(input: RequestInfo | URL, init?: RequestInit) {
  const url = new URL(String(input), "http://localhost");
  const method = init?.method ?? "GET";

  if (url.pathname === "/api/devices" && method === "GET") {
    return jsonResponse({ items: devices });
  }

  if (url.pathname === "/api/devices/scan" && method === "POST") {
    if (scanFails) {
      return jsonResponse(
        {
          error: {
            code: "BLUETOOTH_UNAVAILABLE",
            message: "Bluetooth adapter is unavailable.",
          },
        },
        503,
      );
    }

    return jsonResponse({
      devices: [
        {
          id: "fake-fr935-001",
          is_known: devices.some(
            (device) => device.bluetooth_address === "fake-fr935-001",
          ),
          model_hint: "Forerunner",
          name: "Garmin Forerunner 935",
          rssi: -58,
        },
      ],
    });
  }

  if (url.pathname === "/api/devices/pair" && method === "POST") {
    const body = JSON.parse(String(init?.body ?? "{}")) as {
      bluetooth_device_id: string;
      display_name?: string;
    };
    const device = mockDevice({
      bluetooth_address: body.bluetooth_device_id,
      name: body.display_name ?? "Garmin Forerunner 935",
    });
    devices = [device];
    return jsonResponse(device);
  }

  const settingsMatch = url.pathname.match(/^\/api\/devices\/([^/]+)\/settings$/);
  if (settingsMatch && method === "PATCH") {
    const patch = JSON.parse(
      String(init?.body ?? "{}"),
    ) as DeviceSettingsPatchRequest;
    settingsPatch = patch;
    devices = devices.map((device) =>
      device.id === settingsMatch[1]
        ? { ...device, settings: { ...device.settings, ...patch } }
        : device,
    );
    return jsonResponse(devices[0]);
  }

  const connectionMatch = url.pathname.match(
    /^\/api\/devices\/([^/]+)\/test-connection$/,
  );
  if (connectionMatch && method === "POST") {
    return jsonResponse({
      device_id: connectionMatch[1],
      error_code: null,
      last_seen_at: "2026-06-21T12:00:00Z",
      message: "Connection test succeeded.",
      status: "connected",
      success: true,
    });
  }

  const probeMatch = url.pathname.match(
    /^\/api\/devices\/([^/]+)\/probe-capabilities$/,
  );
  if (probeMatch && method === "POST") {
    const device = devices.find((item) => item.id === probeMatch[1]) ?? devices[0];
    if (!device) {
      return jsonResponse(
        { error: { code: "NOT_FOUND", message: "Missing" } },
        404,
      );
    }
    const capabilities = {
      ...device.capabilities,
      capability_notes: "Direct activity export detected.",
      probed_at: "2026-06-21T12:05:00Z",
      supports_ble_activity_export: true,
    };
    devices = devices.map((item) =>
      item.id === probeMatch[1] ? { ...item, capabilities } : item,
    );
    return jsonResponse(capabilities);
  }

  const capabilitiesMatch = url.pathname.match(
    /^\/api\/devices\/([^/]+)\/capabilities$/,
  );
  if (capabilitiesMatch && method === "GET") {
    const device =
      devices.find((item) => item.id === capabilitiesMatch[1]) ?? devices[0];
    if (!device) {
      return jsonResponse(
        { error: { code: "NOT_FOUND", message: "Missing" } },
        404,
      );
    }
    return jsonResponse(device.capabilities);
  }

  if (url.pathname === "/api/sync-runs" && method === "POST") {
    return jsonResponse({
      activities_imported: 0,
      device_id: devices[0]?.id ?? "mock-device-1",
      duration_seconds: null,
      error_code: null,
      error_summary: null,
      finished_at: null,
      health_records_imported: 0,
      id: "mock-sync-001",
      started_at: "2026-06-21T12:00:00Z",
      status: "running",
    });
  }

  if (url.pathname === "/api/imports/fit-folder" && method === "POST") {
    fitImportRequest = JSON.parse(String(init?.body ?? "{}"));
    return jsonResponse(fitImportResponse);
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

class MockWebSocket {
  static instances: MockWebSocket[] = [];

  onerror: (() => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  url: string;

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
    queueMicrotask(() => {
      for (const event of syncEvents) {
        this.onmessage?.(
          new MessageEvent("message", { data: JSON.stringify(event) }),
        );
      }
    });
  }

  close() {}
}

const syncEvents: SyncProgressEvent[] = [
  {
    message: "Connecting to watch.",
    percent: 15,
    stage: "connecting",
    sync_run_id: "mock-sync-001",
    type: "progress",
  },
  {
    message: "Mock imported 2 activity summaries.",
    percent: 55,
    stage: "importing_activities",
    sync_run_id: "mock-sync-001",
    type: "progress",
  },
  {
    message: "Sync completed successfully.",
    percent: 100,
    stage: "completed",
    sync_run_id: "mock-sync-001",
    type: "completed",
  },
];

function mockDevice(overrides: Partial<Device> = {}): Device {
  return {
    bluetooth_address: "fake-fr935-001",
    capabilities: {
      capability_notes: "Use folder import until direct export is verified.",
      device_id: "mock-device-1",
      probed_at: "2026-06-21T12:00:00Z",
      supports_ble_activity_export: false,
      supports_ble_health_export: false,
      supports_folder_import: true,
    },
    created_at: "2026-06-21T12:00:00Z",
    firmware_version: "21.00",
    id: "mock-device-1",
    last_seen_at: "2026-06-21T12:00:00Z",
    model: "Forerunner 935",
    name: "Garmin Forerunner 935",
    paired_at: "2026-06-21T12:00:00Z",
    serial_number: "FR935-MOCK-001",
    settings: {
      auto_sync_enabled: false,
      device_id: "mock-device-1",
      historical_fit_import_folder: null,
      import_activities: true,
      import_health_stats: true,
      preferred_units: "metric",
      sync_interval_minutes: 60,
    },
    updated_at: "2026-06-21T12:00:00Z",
    ...overrides,
  };
}

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    headers: { "Content-Type": "application/json" },
    status,
  });
}
