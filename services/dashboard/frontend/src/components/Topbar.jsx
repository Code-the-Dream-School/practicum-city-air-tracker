import { aqiTheme } from "../shared/dashboard.js";
import { formatTimestamp } from "../shared/formatters.js";

export function Topbar({ latestTimestamp, selectedCity }) {
  return (
    <header className="topbar">
      <div>
        <div className="eyebrow">City-first dashboard</div>
        <h1 className="topbar__title">
          {selectedCity.city}, {selectedCity.country_code}
        </h1>
      </div>
      <div className="topbar__badges">
        <span
          className="aqi-badge"
          style={{
            backgroundColor: aqiTheme(selectedCity.aqi_category).soft,
            color: aqiTheme(selectedCity.aqi_category).color,
          }}
        >
          {selectedCity.aqi_category}
        </span>
        <span className="topbar__timestamp">Latest data: {formatTimestamp(latestTimestamp)}</span>
      </div>
    </header>
  );
}
