import { BarChart3, Home, TrendingUp } from "lucide-react";

export const PAGE_OPTIONS = [
  { id: "overview", label: "Overview", icon: Home },
  { id: "city-trends", label: "City Trends", icon: TrendingUp },
  { id: "compare", label: "Compare Cities", icon: BarChart3 },
];

export const METRIC_OPTIONS = [
  { value: "aqi", label: "AQI" },
  { value: "pm2_5", label: "PM2.5" },
  { value: "pm10", label: "PM10" },
  { value: "risk_score", label: "Risk Score" },
];

export const AQI_THEME = {
  Good: { color: "#2FA66A", soft: "#E6F8EE" },
  Fair: { color: "#7DBA3C", soft: "#F0F8DF" },
  Moderate: { color: "#F5B83D", soft: "#FFF5DC" },
  Poor: { color: "#F47A42", soft: "#FFE8DD" },
  "Very Poor": { color: "#E4504D", soft: "#FFE3E4" },
  Unknown: { color: "#7A839A", soft: "#EEF1F7" },
};

export const STORAGE_KEYS = {
  activePage: "city-air-active-page",
  metric: "city-air-metric",
  selectedGeoId: "city-air-selected-geo",
};
