import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";

import {
  deleteDataManagementChatHistory,
  deleteImportedDeviceData,
  exportData,
  listDevices,
  queryKeys,
  type DataDeletionResponse,
  type DataExportResponse,
  type Device,
} from "../api/runstats";
import {
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
  StatCard,
} from "../components/StatusViews";
import { formatDateTime } from "../lib/formatters";

export function DataManagementView() {
  const queryClient = useQueryClient();
  const [includeRawFiles, setIncludeRawFiles] = useState(false);
  const [includeChatHistory, setIncludeChatHistory] = useState(false);
  const [selectedDeviceId, setSelectedDeviceId] = useState<string | null>(null);
  const [deviceConfirmation, setDeviceConfirmation] = useState("");

  const devicesQuery = useQuery({
    queryKey: queryKeys.devices.list,
    queryFn: listDevices,
  });
  const devices = useMemo(() => devicesQuery.data?.items ?? [], [devicesQuery.data]);
  const selectedDevice =
    devices.find((device) => device.id === selectedDeviceId) ?? devices[0] ?? null;

  useEffect(() => {
    if (selectedDevice && selectedDevice.id !== selectedDeviceId) {
      setSelectedDeviceId(selectedDevice.id);
      setDeviceConfirmation("");
    }
  }, [selectedDevice, selectedDeviceId]);

  const exportMutation = useMutation({
    mutationFn: () =>
      exportData({
        include_chat_history: includeChatHistory,
        include_raw_files: includeRawFiles,
      }),
    onSuccess: (payload) => {
      downloadExportPayload(payload);
    },
  });

  const chatDeleteMutation = useMutation({
    mutationFn: deleteDataManagementChatHistory,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.chat.all });
    },
  });

  const deviceDeleteMutation = useMutation({
    mutationFn: () => {
      if (!selectedDevice) {
        throw new Error("No device selected.");
      }
      return deleteImportedDeviceData(selectedDevice.id);
    },
    onSuccess: () => {
      setDeviceConfirmation("");
      void queryClient.invalidateQueries({ queryKey: queryKeys.activities.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.health.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.devices.all });
    },
  });

  const deviceDeleteEnabled =
    Boolean(selectedDevice) &&
    deviceConfirmation.trim() === (selectedDevice?.name ?? "") &&
    !deviceDeleteMutation.isPending;

  return (
    <>
      <PageHeader eyebrow="Data Management" title="Local data controls" />

      <section className="data-management-grid">
        <article className="data-panel">
          <div className="panel-heading">
            <h3>Data export</h3>
            <p>{exportMutation.data ? "Export ready" : "JSON"}</p>
          </div>

          <div className="toggle-stack">
            <label className="toggle-row">
              <input
                checked={includeRawFiles}
                onChange={(event) => setIncludeRawFiles(event.target.checked)}
                type="checkbox"
              />
              <span>Include raw archived files</span>
            </label>
            <label className="toggle-row">
              <input
                checked={includeChatHistory}
                onChange={(event) => setIncludeChatHistory(event.target.checked)}
                type="checkbox"
              />
              <span>Include chat history</span>
            </label>
          </div>

          <button
            className="secondary-button"
            disabled={exportMutation.isPending}
            onClick={() => exportMutation.mutate()}
            type="button"
          >
            {exportMutation.isPending ? "Exporting..." : "Export JSON"}
          </button>

          {exportMutation.isError ? (
            <ErrorState error={exportMutation.error} title="Export failed" />
          ) : null}
          {exportMutation.data ? <ExportSummary exportData={exportMutation.data} /> : null}
        </article>

        <article className="data-panel">
          <div className="panel-heading">
            <h3>Chat history</h3>
            <p>{chatDeleteMutation.data ? "Deleted" : "Retained locally"}</p>
          </div>
          <button
            className="secondary-button danger-button"
            disabled={chatDeleteMutation.isPending}
            onClick={() => {
              if (window.confirm("Delete all chat history?")) {
                chatDeleteMutation.mutate();
              }
            }}
            type="button"
          >
            {chatDeleteMutation.isPending ? "Deleting..." : "Delete chat history"}
          </button>
          {chatDeleteMutation.isError ? (
            <ErrorState
              error={chatDeleteMutation.error}
              title="Chat history was not deleted"
            />
          ) : null}
          {chatDeleteMutation.data ? (
            <DeletionSummary deletion={chatDeleteMutation.data} />
          ) : null}
        </article>
      </section>

      <section className="data-panel">
        <div className="panel-heading">
          <h3>Imported device data</h3>
          <p>{deviceDeleteMutation.data ? "Deleted" : "Activities and health"}</p>
        </div>

        {devicesQuery.isLoading ? (
          <LoadingState title="Loading devices" />
        ) : devicesQuery.isError ? (
          <ErrorState error={devicesQuery.error} title="Devices unavailable" />
        ) : selectedDevice ? (
          <DeviceDeletionForm
            confirmation={deviceConfirmation}
            deletion={deviceDeleteMutation.data}
            deleting={deviceDeleteMutation.isPending}
            devices={devices}
            enabled={deviceDeleteEnabled}
            error={deviceDeleteMutation.error}
            onConfirmationChange={setDeviceConfirmation}
            onDelete={() => {
              if (
                window.confirm(
                  `Delete imported data for ${selectedDevice.name}?`,
                )
              ) {
                deviceDeleteMutation.mutate();
              }
            }}
            onSelect={(deviceId) => {
              setSelectedDeviceId(deviceId);
              setDeviceConfirmation("");
            }}
            selectedDevice={selectedDevice}
          />
        ) : (
          <EmptyState title="No devices configured" />
        )}
      </section>
    </>
  );
}

function ExportSummary({ exportData }: { exportData: DataExportResponse }) {
  return (
    <section className="stat-grid stat-grid-compact data-management-summary">
      <StatCard label="Activities" value={String(exportData.counts.activities)} />
      <StatCard label="Health records" value={String(exportData.counts.health_metrics)} />
      <StatCard label="Raw files" value={String(exportData.counts.raw_files)} />
      <StatCard label="Chat messages" value={String(exportData.counts.chat_messages)} />
      <p className="muted-copy form-grid-wide">
        Exported {formatDateTime(exportData.exported_at)}
      </p>
    </section>
  );
}

function DeviceDeletionForm({
  confirmation,
  deleting,
  deletion,
  devices,
  enabled,
  error,
  onConfirmationChange,
  onDelete,
  onSelect,
  selectedDevice,
}: {
  confirmation: string;
  deleting: boolean;
  deletion: DataDeletionResponse | undefined;
  devices: Device[];
  enabled: boolean;
  error: unknown;
  onConfirmationChange: (value: string) => void;
  onDelete: () => void;
  onSelect: (deviceId: string) => void;
  selectedDevice: Device;
}) {
  return (
    <div className="data-management-stack">
      <div className="form-grid">
        <label>
          Device
          <select
            onChange={(event) => onSelect(event.target.value)}
            value={selectedDevice.id}
          >
            {devices.map((device) => (
              <option key={device.id} value={device.id}>
                {device.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Type device name to confirm
          <input
            onChange={(event) => onConfirmationChange(event.target.value)}
            type="text"
            value={confirmation}
          />
        </label>
      </div>
      <section className="stat-grid stat-grid-compact">
        <StatCard label="Model" value={selectedDevice.model} />
        <StatCard
          label="Last seen"
          value={
            selectedDevice.last_seen_at
              ? formatDateTime(selectedDevice.last_seen_at)
              : "Never"
          }
        />
      </section>
      <button
        className="secondary-button danger-button"
        disabled={!enabled}
        onClick={onDelete}
        type="button"
      >
        {deleting ? "Deleting..." : "Delete imported data"}
      </button>
      {error ? <ErrorState error={error} title="Imported data was not deleted" /> : null}
      {deletion ? <DeletionSummary deletion={deletion} /> : null}
    </div>
  );
}

function DeletionSummary({ deletion }: { deletion: DataDeletionResponse }) {
  const parts: string[] = [];
  if (
    deletion.deleted_activities > 0 ||
    deletion.deleted_health_metrics > 0 ||
    deletion.deleted_raw_imports > 0
  ) {
    parts.push(`${deletion.deleted_activities} activities`);
    parts.push(`${deletion.deleted_health_metrics} health records`);
    parts.push(`${deletion.deleted_raw_imports} raw import records`);
  }
  if (deletion.deleted_chat_messages > 0 || deletion.deleted_chat_sessions > 0) {
    parts.push(`${deletion.deleted_chat_messages} chat messages`);
  }
  return (
    <p className="success-copy" role="status">
      Deleted {formatList(parts.length > 0 ? parts : ["0 records"])}.
    </p>
  );
}

function formatList(parts: string[]) {
  if (parts.length <= 2) {
    return parts.join(" and ");
  }
  return `${parts.slice(0, -1).join(", ")}, and ${parts[parts.length - 1]}`;
}

function downloadExportPayload(payload: DataExportResponse) {
  if (typeof URL.createObjectURL !== "function") {
    return;
  }

  const blob = new Blob([JSON.stringify(payload, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `runstats-export-${new Date(payload.exported_at)
    .toISOString()
    .slice(0, 10)}.json`;
  anchor.click();
  URL.revokeObjectURL(url);
}
