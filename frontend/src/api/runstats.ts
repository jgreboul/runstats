type QueryValue = string | number | boolean | null | undefined;

const apiBaseUrl = import.meta.env.VITE_RUNSTATS_API_BASE_URL ?? "";

export type ActivitySummaryBucketName = "day" | "week" | "month" | "year";
export type HealthSeriesBucketName = "day" | "week" | "month";
export type PreferredUnits = "metric" | "imperial";
export type ChatMessageRole = "user" | "assistant" | "system" | "tool";
export type ChatReferenceType = "activity" | "health_metric" | "sync_run" | "chart";
export type DataExportFormatVersion = "runstats.local-data.v1";

export interface ApiErrorBody {
  error?: {
    code?: string;
    message?: string;
    details?: unknown;
  };
}

export class ApiError extends Error {
  code: string;
  details: unknown;
  status: number;

  constructor({
    code,
    details = null,
    message,
    status,
  }: {
    code: string;
    details?: unknown;
    message: string;
    status: number;
  }) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.details = details;
    this.status = status;
  }
}

export interface ActivityListItem {
  id: string;
  device_id: string;
  sport: string;
  name: string;
  started_at: string;
  duration_seconds: number;
  distance_meters: number;
  avg_pace_seconds_per_km: number | null;
  avg_heart_rate: number | null;
  elevation_gain_meters: number | null;
}

export interface ActivityListResponse {
  items: ActivityListItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface ActivityLap {
  id: string;
  lap_index: number;
  started_at: string;
  duration_seconds: number;
  distance_meters: number;
  avg_heart_rate: number | null;
  avg_pace_seconds_per_km: number | null;
}

export interface ActivitySummaryStats {
  distance_kilometers: number;
  avg_speed_meters_per_second: number | null;
  avg_pace_seconds_per_km: number | null;
  lap_count: number;
  sample_count: number;
  gps_sample_count: number;
  has_gps: boolean;
}

export interface ActivityDetailResponse {
  id: string;
  device_id: string;
  source_activity_id: string;
  sport: string;
  name: string;
  started_at: string;
  duration_seconds: number;
  distance_meters: number;
  calories: number | null;
  avg_heart_rate: number | null;
  max_heart_rate: number | null;
  avg_cadence: number | null;
  avg_pace_seconds_per_km: number | null;
  elevation_gain_meters: number | null;
  training_effect: number | null;
  summary: ActivitySummaryStats;
  laps: ActivityLap[];
}

export interface ActivitySample {
  id: number;
  sample_time: string;
  elapsed_seconds: number;
  distance_meters: number | null;
  latitude: number | null;
  longitude: number | null;
  elevation_meters: number | null;
  heart_rate: number | null;
  cadence: number | null;
  power_watts: number | null;
  speed_meters_per_second: number | null;
}

export interface ActivitySamplesResponse {
  activity_id: string;
  samples: ActivitySample[];
}

export interface ActivitySummaryBucket {
  bucket_start: string;
  bucket_end: string;
  activity_count: number;
  distance_meters: number;
  duration_seconds: number;
  avg_pace_seconds_per_km: number | null;
  avg_heart_rate: number | null;
  longest_distance_meters: number;
}

export interface ActivitySummaryResponse {
  bucket: ActivitySummaryBucketName;
  from_time: string | null;
  to_time: string | null;
  total_activities: number;
  total_distance_meters: number;
  total_duration_seconds: number;
  avg_pace_seconds_per_km: number | null;
  avg_heart_rate: number | null;
  buckets: ActivitySummaryBucket[];
}

export interface HealthMetricDescriptor {
  metric_type: string;
  unit: string;
  record_count: number;
  first_start_time: string;
  last_start_time: string;
}

export interface HealthMetricsResponse {
  metrics: HealthMetricDescriptor[];
}

export interface HealthSeriesPoint {
  bucket_start: string;
  bucket_end: string;
  value: number;
  average_value: number;
  total_value: number;
  min_value: number;
  max_value: number;
  record_count: number;
}

export interface HealthSeriesResponse {
  metric_type: string;
  unit: string | null;
  bucket: HealthSeriesBucketName;
  from_time: string | null;
  to_time: string | null;
  metric_available: boolean;
  message: string | null;
  points: HealthSeriesPoint[];
}

export interface SyncRun {
  id: string;
  device_id: string;
  status: string;
  started_at: string;
  finished_at: string | null;
  duration_seconds: number | null;
  activities_imported: number;
  health_records_imported: number;
  error_code: string | null;
  error_summary: string | null;
}

export interface SyncRunListResponse {
  items: SyncRun[];
  total: number;
  limit: number;
  offset: number;
}

export interface ChatReference {
  type: ChatReferenceType;
  id: string;
  label: string;
  href: string;
}

export interface ChatSupportingData {
  intent: string;
  tool_names: string[];
  time_range: string | null;
  metrics: string[];
  row_count: number;
  references: ChatReference[];
  notes: string[];
}

export interface ChatMessage {
  id: string;
  session_id: string;
  role: ChatMessageRole;
  content: string;
  tool_trace: ChatSupportingData | null;
  created_at: string;
}

export interface ChatSessionListItem {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
  message_count: number;
  last_message_preview: string | null;
}

export interface ChatSessionListResponse {
  items: ChatSessionListItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface ChatSession {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
  messages: ChatMessage[];
}

export interface ChatAnswerResponse {
  message_id: string;
  answer: string;
  supporting_data: ChatSupportingData;
}

export interface DiscoveredWatch {
  id: string;
  name: string;
  rssi: number;
  model_hint: string | null;
  is_known: boolean;
}

export interface DeviceScanResponse {
  devices: DiscoveredWatch[];
}

export interface DeviceSettings {
  device_id: string;
  auto_sync_enabled: boolean;
  sync_interval_minutes: number;
  import_activities: boolean;
  import_health_stats: boolean;
  preferred_units: PreferredUnits;
  historical_fit_import_folder: string | null;
}

export interface DeviceCapabilities {
  device_id: string;
  supports_ble_activity_export: boolean;
  supports_ble_health_export: boolean;
  supports_folder_import: boolean;
  capability_notes: string | null;
  probed_at: string | null;
}

export interface Device {
  id: string;
  name: string;
  model: string;
  bluetooth_address: string;
  serial_number: string | null;
  firmware_version: string | null;
  paired_at: string | null;
  last_seen_at: string | null;
  created_at: string;
  updated_at: string;
  settings: DeviceSettings;
  capabilities: DeviceCapabilities;
}

export interface DeviceListResponse {
  items: Device[];
}

export interface DeviceConnectionTestResponse {
  device_id: string;
  status: "connected" | "failed";
  success: boolean;
  message: string;
  last_seen_at: string | null;
  error_code: string | null;
}

export interface DataExportRequest {
  include_raw_files: boolean;
  include_chat_history: boolean;
}

export interface DataExportCounts {
  devices: number;
  activities: number;
  activity_laps: number;
  activity_samples: number;
  health_metrics: number;
  raw_imports: number;
  raw_files: number;
  chat_sessions: number;
  chat_messages: number;
}

export interface DataExportResponse {
  format_version: DataExportFormatVersion;
  exported_at: string;
  include_raw_files: boolean;
  include_chat_history: boolean;
  counts: DataExportCounts;
  devices: unknown[];
  activities: unknown[];
  health_metrics: unknown[];
  raw_imports: unknown[];
  raw_files: unknown[];
  chat_sessions: unknown[];
}

export interface DataDeletionResponse {
  device_id: string | null;
  deleted_activities: number;
  deleted_activity_laps: number;
  deleted_activity_samples: number;
  deleted_health_metrics: number;
  deleted_raw_imports: number;
  deleted_raw_files: number;
  missing_raw_files: number;
  deleted_chat_sessions: number;
  deleted_chat_messages: number;
}

export interface FitFolderImportRequest {
  device_id: string;
  folder_path: string;
  recursive?: boolean;
}

export interface ImportedActivityFileResult {
  source_id: string;
  status: "created" | "skipped" | "failed";
  message: string;
  sha256: string | null;
  activity_id: string | null;
  raw_import_id: string | null;
  archived: boolean;
}

export interface FitFolderImportResponse {
  created: number;
  skipped: number;
  failed: number;
  raw_files_archived: number;
  files: ImportedActivityFileResult[];
}

export interface DeviceScanRequest {
  scan_seconds?: number;
}

export interface DevicePairRequest {
  bluetooth_device_id: string;
  display_name?: string | null;
}

export interface DeviceSettingsPatchRequest {
  auto_sync_enabled?: boolean;
  sync_interval_minutes?: number;
  import_activities?: boolean;
  import_health_stats?: boolean;
  preferred_units?: PreferredUnits;
  historical_fit_import_folder?: string | null;
}

export interface ManualSyncRequest {
  device_id: string;
  include_activities: boolean;
  include_health: boolean;
}

export interface SyncProgressEvent {
  sync_run_id: string;
  type: "progress" | "completed" | "failed";
  stage: string;
  message: string;
  percent: number;
  error_code?: string | null;
}

export interface ActivityListParams {
  from?: string | null;
  to?: string | null;
  sport?: string | null;
  min_distance_meters?: number | null;
  max_distance_meters?: number | null;
  limit?: number;
  offset?: number;
}

export interface ActivitySummaryParams {
  from?: string | null;
  to?: string | null;
  sport?: string | null;
  min_distance_meters?: number | null;
  max_distance_meters?: number | null;
  bucket?: ActivitySummaryBucketName;
}

export interface HealthSeriesParams {
  metric_type: string;
  from?: string | null;
  to?: string | null;
  bucket?: HealthSeriesBucketName;
}

export interface SyncRunListParams {
  device_id?: string | null;
  status?: string | null;
  limit?: number;
  offset?: number;
}

export interface ChatSessionListParams {
  limit?: number;
  offset?: number;
}

// Query key factories stay explicit so cache invalidation can target the
// resource and parameter set without relying on stringly-typed route names.
export const queryKeys = {
  activities: {
    all: ["activities"] as const,
    detail: (activityId: string) =>
      ["activities", "detail", activityId] as const,
    list: (params: ActivityListParams = {}) =>
      ["activities", "list", normalizeActivityListParams(params)] as const,
    samples: (activityId: string) =>
      ["activities", "samples", activityId] as const,
    summary: (params: ActivitySummaryParams = {}) =>
      ["activities", "summary", normalizeActivitySummaryParams(params)] as const,
  },
  health: {
    all: ["health"] as const,
    metrics: ["health", "metrics"] as const,
    series: (params: HealthSeriesParams) =>
      ["health", "series", normalizeHealthSeriesParams(params)] as const,
  },
  syncRuns: {
    all: ["sync-runs"] as const,
    detail: (syncRunId: string) => ["sync-runs", "detail", syncRunId] as const,
    list: (params: SyncRunListParams = {}) =>
      ["sync-runs", "list", normalizeSyncRunListParams(params)] as const,
  },
  chat: {
    all: ["chat"] as const,
    detail: (sessionId: string) => ["chat", "detail", sessionId] as const,
    list: (params: ChatSessionListParams = {}) =>
      ["chat", "list", normalizeChatSessionListParams(params)] as const,
  },
  devices: {
    all: ["devices"] as const,
    capabilities: (deviceId: string) =>
      ["devices", "capabilities", deviceId] as const,
    list: ["devices", "list"] as const,
  },
  dataManagement: {
    all: ["data-management"] as const,
  },
};

export async function listActivities(
  params: ActivityListParams = {},
): Promise<ActivityListResponse> {
  return requestJson<ActivityListResponse>(
    withQuery("/api/activities", normalizeActivityListParams(params)),
  );
}

export async function getActivity(
  activityId: string,
): Promise<ActivityDetailResponse> {
  return requestJson<ActivityDetailResponse>(`/api/activities/${activityId}`);
}

export async function getActivitySamples(
  activityId: string,
): Promise<ActivitySamplesResponse> {
  return requestJson<ActivitySamplesResponse>(
    `/api/activities/${activityId}/samples`,
  );
}

export async function getActivitySummary(
  params: ActivitySummaryParams = {},
): Promise<ActivitySummaryResponse> {
  return requestJson<ActivitySummaryResponse>(
    withQuery("/api/activities/summary", normalizeActivitySummaryParams(params)),
  );
}

export async function listHealthMetrics(): Promise<HealthMetricsResponse> {
  return requestJson<HealthMetricsResponse>("/api/health/metrics");
}

export async function getHealthSeries(
  params: HealthSeriesParams,
): Promise<HealthSeriesResponse> {
  return requestJson<HealthSeriesResponse>(
    withQuery("/api/health/series", normalizeHealthSeriesParams(params)),
  );
}

export async function listSyncRuns(
  params: SyncRunListParams = {},
): Promise<SyncRunListResponse> {
  return requestJson<SyncRunListResponse>(
    withQuery("/api/sync-runs", normalizeSyncRunListParams(params)),
  );
}

export async function getSyncRun(syncRunId: string): Promise<SyncRun> {
  return requestJson<SyncRun>(`/api/sync-runs/${syncRunId}`);
}

export async function createChatSession(
  title?: string | null,
): Promise<ChatSession> {
  return requestJson<ChatSession>("/api/chat/sessions", {
    body: JSON.stringify({ title: title ?? null }),
    method: "POST",
  });
}

export async function listChatSessions(
  params: ChatSessionListParams = {},
): Promise<ChatSessionListResponse> {
  return requestJson<ChatSessionListResponse>(
    withQuery("/api/chat/sessions", normalizeChatSessionListParams(params)),
  );
}

export async function getChatSession(sessionId: string): Promise<ChatSession> {
  return requestJson<ChatSession>(`/api/chat/sessions/${sessionId}`);
}

export async function askChatQuestion(
  sessionId: string,
  message: string,
): Promise<ChatAnswerResponse> {
  return requestJson<ChatAnswerResponse>(
    `/api/chat/sessions/${sessionId}/messages`,
    {
      body: JSON.stringify({ message }),
      method: "POST",
    },
  );
}

export async function deleteChatSession(sessionId: string): Promise<void> {
  await requestJson<void>(`/api/chat/sessions/${sessionId}`, {
    method: "DELETE",
  });
}

export async function deleteChatHistory(): Promise<void> {
  await requestJson<void>("/api/chat/sessions", { method: "DELETE" });
}

export async function scanDevices(
  request: DeviceScanRequest = {},
): Promise<DeviceScanResponse> {
  return requestJson<DeviceScanResponse>("/api/devices/scan", {
    body: JSON.stringify({ scan_seconds: request.scan_seconds ?? 10 }),
    method: "POST",
  });
}

export async function pairDevice(
  request: DevicePairRequest,
): Promise<Device> {
  return requestJson<Device>("/api/devices/pair", {
    body: JSON.stringify(request),
    method: "POST",
  });
}

export async function listDevices(): Promise<DeviceListResponse> {
  return requestJson<DeviceListResponse>("/api/devices");
}

export async function updateDeviceSettings(
  deviceId: string,
  request: DeviceSettingsPatchRequest,
): Promise<Device> {
  return requestJson<Device>(`/api/devices/${deviceId}/settings`, {
    body: JSON.stringify(request),
    method: "PATCH",
  });
}

export async function testDeviceConnection(
  deviceId: string,
): Promise<DeviceConnectionTestResponse> {
  return requestJson<DeviceConnectionTestResponse>(
    `/api/devices/${deviceId}/test-connection`,
    { method: "POST" },
  );
}

export async function probeDeviceCapabilities(
  deviceId: string,
): Promise<DeviceCapabilities> {
  return requestJson<DeviceCapabilities>(
    `/api/devices/${deviceId}/probe-capabilities`,
    { method: "POST" },
  );
}

export async function getDeviceCapabilities(
  deviceId: string,
): Promise<DeviceCapabilities> {
  return requestJson<DeviceCapabilities>(`/api/devices/${deviceId}/capabilities`);
}

export async function exportData(
  request: DataExportRequest,
): Promise<DataExportResponse> {
  return requestJson<DataExportResponse>("/api/data-management/export", {
    body: JSON.stringify(request),
    method: "POST",
  });
}

export async function deleteDataManagementChatHistory(): Promise<DataDeletionResponse> {
  return requestJson<DataDeletionResponse>("/api/data-management/chat-history", {
    method: "DELETE",
  });
}

export async function deleteImportedDeviceData(
  deviceId: string,
): Promise<DataDeletionResponse> {
  return requestJson<DataDeletionResponse>(
    `/api/data-management/devices/${deviceId}/imported-data`,
    { method: "DELETE" },
  );
}

export async function importFitFolder(
  request: FitFolderImportRequest,
): Promise<FitFolderImportResponse> {
  return requestJson<FitFolderImportResponse>("/api/imports/fit-folder", {
    body: JSON.stringify({
      device_id: request.device_id,
      folder_path: request.folder_path,
      recursive: request.recursive ?? true,
    }),
    method: "POST",
  });
}

export async function startSyncRun(
  request: ManualSyncRequest,
): Promise<SyncRun> {
  return requestJson<SyncRun>("/api/sync-runs", {
    body: JSON.stringify(request),
    method: "POST",
  });
}

export async function retrySyncRun(syncRunId: string): Promise<SyncRun> {
  return requestJson<SyncRun>(`/api/sync-runs/${syncRunId}/retry`, {
    method: "POST",
  });
}

export function buildSyncRunEventsUrl(syncRunId: string): string {
  const path = `/api/sync-runs/${syncRunId}/events`;

  if (/^https?:\/\//i.test(apiBaseUrl)) {
    const url = new URL(path, apiBaseUrl);
    url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
    return url.toString();
  }

  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}${apiBaseUrl}${path}`;
}

export async function requestJson<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(buildUrl(path), {
      ...init,
      headers: {
        Accept: "application/json",
        ...(init.body ? { "Content-Type": "application/json" } : {}),
        ...init.headers,
      },
    });
  } catch (error) {
    throw normalizeApiError(error, 0);
  }

  const payload = await parseJson(response);

  if (!response.ok) {
    throw normalizeApiError(payload, response.status);
  }

  return payload as T;
}

export function normalizeApiError(error: unknown, status = 0): ApiError {
  if (error instanceof ApiError) {
    return error;
  }

  if (isApiErrorBody(error) && error.error) {
    return new ApiError({
      code: error.error.code ?? "API_ERROR",
      details: error.error.details ?? null,
      message: error.error.message ?? "The RunStats API returned an error.",
      status,
    });
  }

  if (error instanceof Error) {
    return new ApiError({
      code: status === 0 ? "NETWORK_ERROR" : "API_ERROR",
      message:
        status === 0
          ? "RunStats could not reach the local backend."
          : error.message,
      status,
    });
  }

  return new ApiError({
    code: status === 0 ? "NETWORK_ERROR" : "API_ERROR",
    message:
      status === 0
        ? "RunStats could not reach the local backend."
        : "The RunStats API returned an unexpected response.",
    status,
  });
}

function buildUrl(path: string): string {
  if (/^https?:\/\//i.test(path)) {
    return path;
  }

  return `${apiBaseUrl}${path}`;
}

async function parseJson(response: Response): Promise<unknown> {
  const text = await response.text();
  if (text.length === 0) {
    return null;
  }

  try {
    return JSON.parse(text) as unknown;
  } catch {
    throw new ApiError({
      code: "API_RESPONSE_INVALID",
      message: "The RunStats API returned invalid JSON.",
      status: response.status,
    });
  }
}

function withQuery(path: string, params: Record<string, QueryValue>): string {
  const search = new URLSearchParams();

  for (const [key, value] of Object.entries(params)) {
    if (value !== null && value !== undefined && value !== "") {
      search.set(key, String(value));
    }
  }

  const queryString = search.toString();
  return queryString ? `${path}?${queryString}` : path;
}

function normalizeActivityListParams(params: ActivityListParams) {
  return {
    from: params.from ?? null,
    to: params.to ?? null,
    sport: params.sport ?? null,
    min_distance_meters: params.min_distance_meters ?? null,
    max_distance_meters: params.max_distance_meters ?? null,
    limit: params.limit ?? 50,
    offset: params.offset ?? 0,
  };
}

function normalizeActivitySummaryParams(params: ActivitySummaryParams) {
  return {
    from: params.from ?? null,
    to: params.to ?? null,
    sport: params.sport ?? null,
    min_distance_meters: params.min_distance_meters ?? null,
    max_distance_meters: params.max_distance_meters ?? null,
    bucket: params.bucket ?? "week",
  };
}

function normalizeHealthSeriesParams(params: HealthSeriesParams) {
  return {
    metric_type: params.metric_type,
    from: params.from ?? null,
    to: params.to ?? null,
    bucket: params.bucket ?? "day",
  };
}

function normalizeSyncRunListParams(params: SyncRunListParams) {
  return {
    device_id: params.device_id ?? null,
    status: params.status ?? null,
    limit: params.limit ?? 20,
    offset: params.offset ?? 0,
  };
}

function normalizeChatSessionListParams(params: ChatSessionListParams) {
  return {
    limit: params.limit ?? 20,
    offset: params.offset ?? 0,
  };
}

function isApiErrorBody(error: unknown): error is ApiErrorBody {
  return (
    typeof error === "object" &&
    error !== null &&
    "error" in error &&
    (typeof (error as ApiErrorBody).error === "object" ||
      (error as ApiErrorBody).error === undefined)
  );
}
