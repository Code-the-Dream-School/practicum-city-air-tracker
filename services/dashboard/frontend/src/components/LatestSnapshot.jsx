import { AlertTriangle, CloudSun, Gauge, Wind } from "lucide-react";
import { CityRankCard } from "./CityRankCard.jsx";
import { StatPill } from "./StatPill.jsx";
import { aqiTheme } from "../shared/dashboard.js";
import { formatMetricValue, formatTimestamp } from "../shared/formatters.js";

export function LatestSnapshot({ city, latestByCity, latestTimestamp }) {
  const theme = aqiTheme(city.aqi_category);

  return (
    <section className="panel panel--soft">
      <div className="snapshot__top">
        <div>
          <div className="eyebrow">Current Snapshot</div>
          <h2 className="panel-title">
            {city.city}, {city.country_code}
          </h2>
        </div>
        <span className="aqi-badge" style={{ backgroundColor: theme.soft, color: theme.color }}>
          {city.aqi_category ?? "Unknown"}
        </span>
      </div>

      <div className="snapshot__big-number">
        <span className="snapshot__label">AQI</span>
        <span className="snapshot__value">{formatMetricValue(city.aqi, "aqi")}</span>
      </div>

      <div className="snapshot__grid">
        <StatPill label="Risk Score" value={formatMetricValue(city.risk_score, "risk_score")} icon={AlertTriangle} />
        <StatPill label="PM2.5" value={formatMetricValue(city.pm2_5, "pm2_5")} icon={Wind} />
        <StatPill label="PM10" value={formatMetricValue(city.pm10, "pm10")} icon={CloudSun} />
        <StatPill label="24h Avg" value={formatMetricValue(city.pm2_5_24h_avg, "pm2_5")} icon={Gauge} />
      </div>

      <div className="snapshot__footer">
        Updated {formatTimestamp(city.ts)} · Dataset refreshed {formatTimestamp(latestTimestamp)}
      </div>
      <CityRankCard latestByCity={latestByCity} selectedCity={city} />
    </section>
  );
}
