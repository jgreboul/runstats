import { afterEach, describe, expect, it, vi } from "vitest";

import {
  ApiError,
  askChatQuestion,
  createChatSession,
  deleteDataManagementChatHistory,
  deleteChatHistory,
  deleteImportedDeviceData,
  exportData,
  getActivity,
  getChatSession,
  getDeviceCapabilities,
  listChatSessions,
  listActivities,
  normalizeApiError,
  probeDeviceCapabilities,
  queryKeys,
  scanDevices,
} from "../src/api/runstats";

describe("RunStats API client", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("serializes typed request parameters", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = new URL(String(input), "http://localhost");

      expect(url.pathname).toBe("/api/activities");
      expect(url.searchParams.get("limit")).toBe("10");
      expect(url.searchParams.get("offset")).toBe("5");
      expect(url.searchParams.get("sport")).toBe("running");

      return jsonResponse({ items: [], limit: 10, offset: 5, total: 0 });
    });
    vi.stubGlobal("fetch", fetchMock);

    const response = await listActivities({
      limit: 10,
      offset: 5,
      sport: "running",
    });

    expect(response.total).toBe(0);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("posts device scan requests", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = new URL(String(input), "http://localhost");

      expect(url.pathname).toBe("/api/devices/scan");
      expect(init?.method).toBe("POST");
      expect(JSON.parse(String(init?.body))).toEqual({ scan_seconds: 5 });

      return jsonResponse({ devices: [] });
    });
    vi.stubGlobal("fetch", fetchMock);

    const response = await scanDevices({ scan_seconds: 5 });

    expect(response.devices).toEqual([]);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("reads and posts device capability requests", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = new URL(String(input), "http://localhost");

      if (url.pathname.endsWith("/probe-capabilities")) {
        expect(url.pathname).toBe("/api/devices/device-1/probe-capabilities");
        expect(init?.method).toBe("POST");
      } else {
        expect(url.pathname).toBe("/api/devices/device-1/capabilities");
        expect(init?.method).toBeUndefined();
      }

      return jsonResponse({
        capability_notes: null,
        device_id: "device-1",
        probed_at: null,
        supports_ble_activity_export: false,
        supports_ble_health_export: false,
        supports_folder_import: true,
      });
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(probeDeviceCapabilities("device-1")).resolves.toMatchObject({
      supports_folder_import: true,
    });
    await expect(getDeviceCapabilities("device-1")).resolves.toMatchObject({
      device_id: "device-1",
    });
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("reads and mutates chat resources", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = new URL(String(input), "http://localhost");

      if (url.pathname === "/api/chat/sessions" && init?.method === "POST") {
        expect(JSON.parse(String(init?.body))).toEqual({ title: "New chat" });
        return jsonResponse(chatSession([]));
      }

      if (url.pathname === "/api/chat/sessions" && init?.method === "DELETE") {
        return new Response(null, { status: 204 });
      }

      if (url.pathname === "/api/chat/sessions") {
        expect(url.searchParams.get("limit")).toBe("5");
        return jsonResponse({ items: [], limit: 5, offset: 0, total: 0 });
      }

      if (url.pathname === "/api/chat/sessions/session-1/messages") {
        expect(init?.method).toBe("POST");
        expect(JSON.parse(String(init?.body))).toEqual({ message: "Longest run?" });
        return jsonResponse({
          answer: "Longest run: Sunday Long Run.",
          message_id: "assistant-1",
          supporting_data: supportingData,
        });
      }

      expect(url.pathname).toBe("/api/chat/sessions/session-1");
      return jsonResponse(chatSession([]));
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(createChatSession("New chat")).resolves.toMatchObject({
      id: "session-1",
    });
    await expect(listChatSessions({ limit: 5 })).resolves.toMatchObject({
      total: 0,
    });
    await expect(getChatSession("session-1")).resolves.toMatchObject({
      id: "session-1",
    });
    await expect(askChatQuestion("session-1", "Longest run?")).resolves.toMatchObject({
      supporting_data: { intent: "longest_run" },
    });
    await expect(deleteChatHistory()).resolves.toBeUndefined();
    expect(fetchMock).toHaveBeenCalledTimes(5);
  });

  it("exports and deletes local data-management resources", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = new URL(String(input), "http://localhost");

      if (url.pathname === "/api/data-management/export") {
        expect(init?.method).toBe("POST");
        expect(JSON.parse(String(init?.body))).toEqual({
          include_chat_history: true,
          include_raw_files: false,
        });
        return jsonResponse({
          activities: [],
          chat_sessions: [],
          counts: {
            activities: 0,
            activity_laps: 0,
            activity_samples: 0,
            chat_messages: 0,
            chat_sessions: 0,
            devices: 0,
            health_metrics: 0,
            raw_files: 0,
            raw_imports: 0,
          },
          devices: [],
          exported_at: "2026-06-22T12:00:00Z",
          format_version: "runstats.local-data.v1",
          health_metrics: [],
          include_chat_history: true,
          include_raw_files: false,
          raw_files: [],
          raw_imports: [],
        });
      }

      if (url.pathname === "/api/data-management/chat-history") {
        expect(init?.method).toBe("DELETE");
        return jsonResponse(deletionResponse({ deleted_chat_messages: 2 }));
      }

      expect(url.pathname).toBe(
        "/api/data-management/devices/device-1/imported-data",
      );
      expect(init?.method).toBe("DELETE");
      return jsonResponse(deletionResponse({ deleted_activities: 3 }));
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      exportData({ include_chat_history: true, include_raw_files: false }),
    ).resolves.toMatchObject({
      format_version: "runstats.local-data.v1",
      include_chat_history: true,
    });
    await expect(deleteDataManagementChatHistory()).resolves.toMatchObject({
      deleted_chat_messages: 2,
    });
    await expect(deleteImportedDeviceData("device-1")).resolves.toMatchObject({
      deleted_activities: 3,
    });
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it("normalizes structured backend errors", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        jsonResponse(
          {
            error: {
              code: "ACTIVITY_NOT_FOUND",
              details: { activity_id: "missing" },
              message: "Activity not found.",
            },
          },
          404,
        ),
      ),
    );

    await expect(getActivity("missing")).rejects.toMatchObject({
      code: "ACTIVITY_NOT_FOUND",
      details: { activity_id: "missing" },
      message: "Activity not found.",
      status: 404,
    });
  });

  it("normalizes network failures", () => {
    const error = normalizeApiError(new Error("fetch failed"));

    expect(error).toBeInstanceOf(ApiError);
    expect(error.code).toBe("NETWORK_ERROR");
    expect(error.message).toBe("RunStats could not reach the local backend.");
  });

  it("documents stable query key shapes", () => {
    expect(queryKeys.activities.list({ limit: 5 })).toEqual([
      "activities",
      "list",
      {
        from: null,
        limit: 5,
        max_distance_meters: null,
        min_distance_meters: null,
        offset: 0,
        sport: null,
        to: null,
      },
    ]);
    expect(queryKeys.health.series({ metric_type: "steps" })).toEqual([
      "health",
      "series",
      {
        bucket: "day",
        from: null,
        metric_type: "steps",
        to: null,
      },
    ]);
    expect(queryKeys.devices.list).toEqual(["devices", "list"]);
    expect(queryKeys.devices.capabilities("device-1")).toEqual([
      "devices",
      "capabilities",
      "device-1",
    ]);
    expect(queryKeys.chat.detail("session-1")).toEqual([
      "chat",
      "detail",
      "session-1",
    ]);
  });
});

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    headers: { "Content-Type": "application/json" },
    status,
  });
}

const supportingData = {
  intent: "longest_run",
  metrics: ["running_distance"],
  notes: [],
  references: [],
  row_count: 1,
  time_range: null,
  tool_names: ["longest_run"],
};

function chatSession(messages: unknown[]) {
  return {
    created_at: "2026-06-15T10:00:00Z",
    id: "session-1",
    messages,
    title: "New chat",
    updated_at: "2026-06-15T10:00:00Z",
  };
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
