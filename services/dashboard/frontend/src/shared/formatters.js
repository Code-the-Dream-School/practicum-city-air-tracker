export function formatMetricValue(value, metric) {
  if (value == null || Number.isNaN(value)) {
    return "--";
  }

  if (metric === "aqi") {
    return `${Math.round(value)}`;
  }

  return `${value.toFixed(1)}`;
}

export function formatTimestamp(value) {
  if (!value) {
    return "--";
  }

  const date = new Date(value);
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}

export function formatAxisTimestamp(value) {
  const date = new Date(value);
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
  }).format(date);
}
