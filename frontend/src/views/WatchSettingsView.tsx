import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";

import {
  ApiError,
  buildSyncRunEventsUrl,
  listDevices,
  pairDevice,
  probeDeviceCapabilities,
  queryKeys,
  scanDevices,
  startSyncRun,
  testDeviceConnection,
  updateDeviceSettings,
  type Device,
  type DeviceConnectionTestResponse,
  type DeviceSettingsPatchRequest,
  type DiscoveredWatch,
  type PreferredUnits,
  type SyncProgressEvent,
  type SyncRun,
} from "../api/runstats";
import {
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
  StatCard,
} from "../components/StatusViews";
import { formatDateTime, formatStatus } from "../lib/formatters";

type SyncStatus = "idle" | "syncing" | "succeeded" | "failed";

interface SettingsFormState {
  auto_sync_enabled: boolean;
  sync_interval_minutes: number;
  import_activities: boolean;
  import_health_stats: boolean;
  preferred_units: PreferredUnits;
  historical_fit_import_folder: string;
}

const emptyForm: SettingsFormState = {
  auto_sync_enabled: false,
  sync_interval_minutes: 60,
  import_activities: true,
  import_health_stats: true,
  preferred_units: "metric",
  historical_fit_import_folder: "",
};

export function WatchSettingsView() {
  const queryClient = useQueryClient();
  const socketRef = useRef<WebSocket | null>(null);
  const [selectedDeviceId, setSelectedDeviceId] = useState<string | null>(null);
  const [settingsForm, setSettingsForm] = useState<SettingsFormState>(emptyForm);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [connectionResult, setConnectionResult] =
    useState<DeviceConnectionTestResponse | null>(null);
  const [activeSync, setActiveSync] = useState<SyncRun | null>(null);
  const [syncEvents, setSyncEvents] = useState<SyncProgressEvent[]>([]);
  const [syncStatus, setSyncStatus] = useState<SyncStatus>("idle");
  const [syncError, setSyncError] = useState<string | null>(null);

  const devicesQuery = useQuery({
    queryKey: queryKeys.devices.list,
    queryFn: listDevices,
  });

  const devices = devicesQuery.data?.items ?? [];
  const selectedDevice =
    devices.find((device) => device.id === selectedDeviceId) ?? devices[0] ?? null;

  useEffect(() => {
    if (selectedDevice && selectedDevice.id !== selectedDeviceId) {
      setSelectedDeviceId(selectedDevice.id);
    }
  }, [selectedDevice, selectedDeviceId]);

  useEffect(() => {
    if (selectedDevice) {
      setSettingsForm(formFromDevice(selectedDevice));
      setSaveMessage(null);
    }
  }, [selectedDevice]);

  useEffect(() => {
    return () => {
      socketRef.current?.close();
    };
  }, []);

  const scanMutation = useMutation({
    mutationFn: () => scanDevices({ scan_seconds: 10 }),
  });

  const pairMutation = useMutation({
    mutationFn: (watch: DiscoveredWatch) =>
      pairDevice({
        bluetooth_device_id: watch.id,
        display_name: watch.name,
      }),
    onSuccess: (device) => {
      setSelectedDeviceId(device.id);
      setConnectionResult(null);
      void queryClient.invalidateQueries({ queryKey: queryKeys.devices.all });
    },
  });

  const settingsMutation = useMutation({
    mutationFn: (patch: DeviceSettingsPatchRequest) => {
      if (!selectedDevice) {
        throw new Error("No watch selected.");
      }
      return updateDeviceSettings(selectedDevice.id, patch);
    },
    onSuccess: (device) => {
      setSelectedDeviceId(device.id);
      setSaveMessage("Settings saved.");
      void queryClient.invalidateQueries({ queryKey: queryKeys.devices.all });
    },
  });

  const connectionMutation = useMutation({
    mutationFn: () => {
      if (!selectedDevice) {
        throw new Error("No watch selected.");
      }
      return testDeviceConnection(selectedDevice.id);
    },
    onSuccess: (result) => {
      setConnectionResult(result);
      void queryClient.invalidateQueries({ queryKey: queryKeys.devices.all });
    },
  });

  const capabilityMutation = useMutation({
    mutationFn: () => {
      if (!selectedDevice) {
        throw new Error("No watch selected.");
      }
      return probeDeviceCapabilities(selectedDevice.id);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.devices.all });
    },
  });

  const syncMutation = useMutation({
    mutationFn: () => {
      if (!selectedDevice) {
        throw new Error("No watch selected.");
      }
      return startSyncRun({
        device_id: selectedDevice.id,
        include_activities: settingsForm.import_activities,
        include_health: settingsForm.import_health_stats,
      });
    },
    onSuccess: (syncRun) => {
      setActiveSync(syncRun);
      setSyncEvents([]);
      setSyncError(null);
      setSyncStatus("syncing");
      connectToSyncEvents(syncRun);
      void queryClient.invalidateQueries({ queryKey: queryKeys.syncRuns.all });
    },
    onError: (error) => {
      setSyncStatus("failed");
      setSyncError(error instanceof Error ? error.message : "Manual sync failed.");
    },
  });

  function connectToSyncEvents(syncRun: SyncRun) {
    socketRef.current?.close();
    const socket = new WebSocket(buildSyncRunEventsUrl(syncRun.id));
    socketRef.current = socket;

    socket.onmessage = (message) => {
      const event = JSON.parse(String(message.data)) as SyncProgressEvent;
      setSyncEvents((current) => [...current, event]);
      if (event.type === "completed") {
        setSyncStatus("succeeded");
        socket.close();
        void queryClient.invalidateQueries({ queryKey: queryKeys.syncRuns.all });
      }
      if (event.type === "failed") {
        setSyncStatus("failed");
        setSyncError(event.message);
        socket.close();
        void queryClient.invalidateQueries({ queryKey: queryKeys.syncRuns.all });
      }
    };

    socket.onerror = () => {
      setSyncStatus("failed");
      setSyncError("Sync progress stream failed.");
    };
  }

  const lastSyncEvent = syncEvents[syncEvents.length - 1] ?? null;
  const canStartSync =
    Boolean(selectedDevice) &&
    (settingsForm.import_activities || settingsForm.import_health_stats) &&
    syncStatus !== "syncing" &&
    !syncMutation.isPending;

  return (
    <>
      <PageHeader eyebrow="Watch Settings" title="Garmin watch setup" />

      <section className="watch-layout">
        <article className="data-panel">
          <div className="panel-heading">
            <h3>Discovery</h3>
            <p>{scanMutation.isPending ? "Scanning" : "Bluetooth provider"}</p>
          </div>

          <button
            className="secondary-button"
            disabled={scanMutation.isPending}
            onClick={() => scanMutation.mutate()}
            type="button"
          >
            {scanMutation.isPending ? "Scanning..." : "Scan"}
          </button>

          {scanMutation.isError ? (
            <ErrorState
              error={scanMutation.error}
              title={scanErrorTitle(scanMutation.error)}
            />
          ) : null}

          {scanMutation.data ? (
            <WatchScanResults
              isPairing={pairMutation.isPending}
              onPair={(watch) => pairMutation.mutate(watch)}
              watches={scanMutation.data.devices}
            />
          ) : null}

          {pairMutation.isError ? (
            <ErrorState error={pairMutation.error} title="Pairing failed" />
          ) : null}
        </article>

        <article className="data-panel">
          <div className="panel-heading">
            <h3>Configured watch</h3>
            <p>{devices.length} saved</p>
          </div>

          {devicesQuery.isLoading ? (
            <LoadingState title="Loading watches" />
          ) : devicesQuery.isError ? (
            <ErrorState error={devicesQuery.error} title="Watch settings unavailable" />
          ) : selectedDevice ? (
            <ConfiguredWatch
              capabilityError={capabilityMutation.error}
              connectionResult={connectionResult}
              device={selectedDevice}
              devices={devices}
              onSelect={setSelectedDeviceId}
              probeCapabilities={() => capabilityMutation.mutate()}
              probingCapabilities={capabilityMutation.isPending}
              testConnection={() => connectionMutation.mutate()}
              testingConnection={connectionMutation.isPending}
            />
          ) : (
            <EmptyState
              message="Scanned and paired watches will appear here."
              title="No watch configured"
            />
          )}
        </article>
      </section>

      {selectedDevice ? (
        <section className="watch-layout watch-layout-wide">
          <article className="data-panel">
            <div className="panel-heading">
              <h3>Sync settings</h3>
              <p>{saveMessage ?? "Local preferences"}</p>
            </div>
            <SettingsForm
              disabled={settingsMutation.isPending}
              form={settingsForm}
              onChange={setSettingsForm}
              onSubmit={() =>
                settingsMutation.mutate(settingsPatchFromForm(settingsForm))
              }
            />
            {settingsMutation.isError ? (
              <ErrorState error={settingsMutation.error} title="Settings not saved" />
            ) : null}
          </article>

          <article className="data-panel">
            <div className="panel-heading">
              <h3>Manual sync</h3>
              <p>{activeSync ? formatStatus(activeSync.status) : "Ready"}</p>
            </div>
            <section className="stat-grid stat-grid-compact" aria-label="Sync controls">
              <StatCard
                label="Activity import"
                value={settingsForm.import_activities ? "Enabled" : "Off"}
              />
              <StatCard
                label="Health import"
                value={settingsForm.import_health_stats ? "Enabled" : "Off"}
              />
            </section>
            <button
              className="secondary-button"
              disabled={!canStartSync}
              onClick={() => syncMutation.mutate()}
              type="button"
            >
              {syncStatus === "syncing" ? "Syncing..." : "Start sync"}
            </button>
            <SyncProgress
              error={syncError}
              event={lastSyncEvent}
              status={syncStatus}
            />
          </article>
        </section>
      ) : null}
    </>
  );
}

function WatchScanResults({
  isPairing,
  onPair,
  watches,
}: {
  isPairing: boolean;
  onPair: (watch: DiscoveredWatch) => void;
  watches: DiscoveredWatch[];
}) {
  if (watches.length === 0) {
    return <EmptyState title="No watches found" />;
  }

  return (
    <div className="watch-list" aria-label="Discovered watches">
      {watches.map((watch) => (
        <div className="watch-list-row" key={watch.id}>
          <div>
            <strong>{watch.name}</strong>
            <span>
              {watch.model_hint ?? "Garmin"} - RSSI {watch.rssi} -{" "}
              {watch.is_known ? "Known" : "New"}
            </span>
          </div>
          <button
            className="secondary-button"
            disabled={isPairing}
            onClick={() => onPair(watch)}
            type="button"
          >
            {isPairing ? "Pairing..." : `Pair ${watch.name}`}
          </button>
        </div>
      ))}
    </div>
  );
}

function ConfiguredWatch({
  capabilityError,
  connectionResult,
  device,
  devices,
  onSelect,
  probeCapabilities,
  probingCapabilities,
  testConnection,
  testingConnection,
}: {
  capabilityError: unknown;
  connectionResult: DeviceConnectionTestResponse | null;
  device: Device;
  devices: Device[];
  onSelect: (deviceId: string) => void;
  probeCapabilities: () => void;
  probingCapabilities: boolean;
  testConnection: () => void;
  testingConnection: boolean;
}) {
  return (
    <div className="watch-stack">
      {devices.length > 1 ? (
        <label>
          Watch
          <select
            value={device.id}
            onChange={(event) => onSelect(event.target.value)}
          >
            {devices.map((storedDevice) => (
              <option key={storedDevice.id} value={storedDevice.id}>
                {storedDevice.name}
              </option>
            ))}
          </select>
        </label>
      ) : null}

      <section className="stat-grid stat-grid-compact" aria-label="Watch summary">
        <StatCard label="Model" value={device.model} />
        <StatCard
          label="Last seen"
          value={device.last_seen_at ? formatDateTime(device.last_seen_at) : "Never"}
        />
      </section>

      <CapabilityList
        device={device}
        error={capabilityError}
        onProbe={probeCapabilities}
        probing={probingCapabilities}
      />

      <button
        className="secondary-button"
        disabled={testingConnection}
        onClick={testConnection}
        type="button"
      >
        {testingConnection ? "Testing..." : "Test connection"}
      </button>

      {connectionResult ? (
        <div
          className={`connection-result connection-result-${connectionResult.status}`}
          role={connectionResult.success ? "status" : "alert"}
        >
          <strong>
            {connectionResult.success ? "Connected" : "Connection failed"}
          </strong>
          <p>{connectionResult.message}</p>
        </div>
      ) : null}
    </div>
  );
}

function CapabilityList({
  device,
  error,
  onProbe,
  probing,
}: {
  device: Device;
  error: unknown;
  onProbe: () => void;
  probing: boolean;
}) {
  const capabilities = [
    {
      label: "Direct BLE activity export",
      supported: device.capabilities.supports_ble_activity_export,
    },
    {
      label: "Direct BLE health export",
      supported: device.capabilities.supports_ble_health_export,
    },
    {
      label: "Folder import",
      supported: device.capabilities.supports_folder_import,
    },
  ];

  return (
    <div>
      <div className="capability-grid" aria-label="Import capabilities">
        {capabilities.map((capability) => (
          <div className="capability-row" key={capability.label}>
            <span>{capability.label}</span>
            <strong>{capability.supported ? "Supported" : "Unavailable"}</strong>
          </div>
        ))}
      </div>
      {device.capabilities.capability_notes ? (
        <p className="muted-copy">{device.capabilities.capability_notes}</p>
      ) : null}
      <div className="capability-actions">
        <button
          className="secondary-button"
          disabled={probing}
          onClick={onProbe}
          type="button"
        >
          {probing ? "Probing..." : "Probe capabilities"}
        </button>
        {device.capabilities.probed_at ? (
          <span>Last probed {formatDateTime(device.capabilities.probed_at)}</span>
        ) : null}
      </div>
      {error ? <ErrorState error={error} title="Capability probe failed" /> : null}
    </div>
  );
}

function SettingsForm({
  disabled,
  form,
  onChange,
  onSubmit,
}: {
  disabled: boolean;
  form: SettingsFormState;
  onChange: (form: SettingsFormState) => void;
  onSubmit: () => void;
}) {
  return (
    <form
      className="watch-settings-form"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
    >
      <div className="toggle-stack">
        <label className="toggle-row">
          <input
            checked={form.auto_sync_enabled}
            onChange={(event) =>
              onChange({ ...form, auto_sync_enabled: event.target.checked })
            }
            type="checkbox"
          />
          <span>Automatic sync</span>
        </label>
        <label className="toggle-row">
          <input
            checked={form.import_activities}
            onChange={(event) =>
              onChange({ ...form, import_activities: event.target.checked })
            }
            type="checkbox"
          />
          <span>Import activities</span>
        </label>
        <label className="toggle-row">
          <input
            checked={form.import_health_stats}
            onChange={(event) =>
              onChange({ ...form, import_health_stats: event.target.checked })
            }
            type="checkbox"
          />
          <span>Import health stats</span>
        </label>
      </div>

      <div className="form-grid">
        <label>
          Sync interval
          <input
            min="5"
            onChange={(event) =>
              onChange({
                ...form,
                sync_interval_minutes: Number(event.target.value),
              })
            }
            type="number"
            value={form.sync_interval_minutes}
          />
        </label>
        <label>
          Preferred units
          <select
            onChange={(event) =>
              onChange({
                ...form,
                preferred_units: event.target.value as PreferredUnits,
              })
            }
            value={form.preferred_units}
          >
            <option value="metric">Metric</option>
            <option value="imperial">Imperial</option>
          </select>
        </label>
        <label className="form-grid-wide">
          Historical FIT import folder
          <input
            onChange={(event) =>
              onChange({
                ...form,
                historical_fit_import_folder: event.target.value,
              })
            }
            type="text"
            value={form.historical_fit_import_folder}
          />
        </label>
      </div>

      <button className="secondary-button" disabled={disabled} type="submit">
        {disabled ? "Saving..." : "Save settings"}
      </button>
    </form>
  );
}

function SyncProgress({
  error,
  event,
  status,
}: {
  error: string | null;
  event: SyncProgressEvent | null;
  status: SyncStatus;
}) {
  if (status === "idle" && !event) {
    return <EmptyState title="No manual sync running" />;
  }

  const percent = event?.percent ?? 0;
  const title =
    status === "succeeded"
      ? "Sync succeeded"
      : status === "failed"
        ? "Sync failed"
        : "Syncing";

  return (
    <div className={`sync-progress sync-progress-${status}`}>
      <div className="panel-heading">
        <h3>{title}</h3>
        <p>{percent}%</p>
      </div>
      <div className="progress-track" aria-label="Sync progress">
        <div className="progress-fill" style={{ width: `${percent}%` }} />
      </div>
      <p>{error ?? event?.message ?? "Preparing sync."}</p>
    </div>
  );
}

function formFromDevice(device: Device): SettingsFormState {
  return {
    auto_sync_enabled: device.settings.auto_sync_enabled,
    sync_interval_minutes: device.settings.sync_interval_minutes,
    import_activities: device.settings.import_activities,
    import_health_stats: device.settings.import_health_stats,
    preferred_units: device.settings.preferred_units,
    historical_fit_import_folder:
      device.settings.historical_fit_import_folder ?? "",
  };
}

function settingsPatchFromForm(
  form: SettingsFormState,
): DeviceSettingsPatchRequest {
  return {
    auto_sync_enabled: form.auto_sync_enabled,
    sync_interval_minutes: form.sync_interval_minutes,
    import_activities: form.import_activities,
    import_health_stats: form.import_health_stats,
    preferred_units: form.preferred_units,
    historical_fit_import_folder:
      form.historical_fit_import_folder.trim() || null,
  };
}

function scanErrorTitle(error: unknown): string {
  if (error instanceof ApiError && error.code === "BLUETOOTH_UNAVAILABLE") {
    return "Bluetooth unavailable";
  }
  return "Watch scan failed";
}
