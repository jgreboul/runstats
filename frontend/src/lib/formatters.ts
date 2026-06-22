const dateFormatter = new Intl.DateTimeFormat("en-US", {
  day: "numeric",
  month: "short",
  year: "numeric",
});

const dateTimeFormatter = new Intl.DateTimeFormat("en-US", {
  day: "numeric",
  hour: "numeric",
  minute: "2-digit",
  month: "short",
  year: "numeric",
});

export function formatDate(value: string | null | undefined): string {
  if (!value) {
    return "Not available";
  }

  return dateFormatter.format(new Date(value));
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return "Not available";
  }

  return dateTimeFormatter.format(new Date(value));
}

export function formatShortDate(value: string | null | undefined): string {
  if (!value) {
    return "N/A";
  }

  return new Intl.DateTimeFormat("en-US", {
    day: "numeric",
    month: "short",
  }).format(new Date(value));
}

export function formatShortDateUtc(value: string | null | undefined): string {
  if (!value) {
    return "N/A";
  }

  return new Intl.DateTimeFormat("en-US", {
    day: "numeric",
    month: "short",
    timeZone: "UTC",
  }).format(new Date(value));
}

export function formatDistance(meters: number | null | undefined): string {
  if (!isFiniteNumber(meters)) {
    return "Not available";
  }

  const kilometers = meters / 1000;
  const precision = kilometers >= 10 ? 1 : 2;
  return `${kilometers.toFixed(precision)} km`;
}

export function formatDuration(seconds: number | null | undefined): string {
  if (!isFiniteNumber(seconds)) {
    return "Not available";
  }

  const roundedSeconds = Math.round(seconds);
  const hours = Math.floor(roundedSeconds / 3600);
  const minutes = Math.floor((roundedSeconds % 3600) / 60);
  const remainingSeconds = roundedSeconds % 60;

  if (hours > 0) {
    return `${hours}h ${minutes.toString().padStart(2, "0")}m`;
  }

  return `${minutes}:${remainingSeconds.toString().padStart(2, "0")}`;
}

export function formatPace(
  secondsPerKilometer: number | null | undefined,
): string {
  if (!isFiniteNumber(secondsPerKilometer)) {
    return "Not available";
  }

  const roundedSeconds = Math.round(secondsPerKilometer);
  const minutes = Math.floor(roundedSeconds / 60);
  const seconds = roundedSeconds % 60;
  return `${minutes}:${seconds.toString().padStart(2, "0")} /km`;
}

export function formatNumber(
  value: number | null | undefined,
  suffix = "",
  precision = 0,
): string {
  if (!isFiniteNumber(value)) {
    return "Not available";
  }

  return `${value.toFixed(precision)}${suffix}`;
}

export function formatSport(sport: string): string {
  return sport
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

export function formatStatus(status: string): string {
  return formatSport(status);
}

export function toStartOfDayIso(value: string): string | null {
  return value ? `${value}T00:00:00Z` : null;
}

export function toEndOfDayIso(value: string): string | null {
  return value ? `${value}T23:59:59Z` : null;
}

export function kilometersToMeters(value: string): number | null {
  if (value.trim() === "") {
    return null;
  }

  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed * 1000 : null;
}

export function secondsPerKilometerToMinutes(
  secondsPerKilometer: number | null | undefined,
): number | null {
  if (!isFiniteNumber(secondsPerKilometer)) {
    return null;
  }

  return Number((secondsPerKilometer / 60).toFixed(2));
}

export function speedToPaceMinutes(
  metersPerSecond: number | null | undefined,
): number | null {
  if (!isFiniteNumber(metersPerSecond) || metersPerSecond <= 0) {
    return null;
  }

  return Number((1000 / metersPerSecond / 60).toFixed(2));
}

function isFiniteNumber(value: number | null | undefined): value is number {
  return typeof value === "number" && Number.isFinite(value);
}
