import { AQI_THEME } from "./constants.js";

export function aqiTheme(category) {
  return AQI_THEME[category] ?? AQI_THEME.Unknown;
}

export function sortByMetric(rows, metric) {
  return [...rows].sort((a, b) => (b[metric] ?? 0) - (a[metric] ?? 0));
}
