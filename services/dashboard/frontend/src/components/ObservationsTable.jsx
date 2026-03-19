import { aqiTheme } from "../shared/dashboard.js";
import { formatMetricValue, formatTimestamp } from "../shared/formatters.js";

export function ObservationsTable({ rows }) {
  const preview = rows.slice(-8).reverse();

  return (
    <section className="panel">
      <div className="panel__header">
        <div>
          <div className="eyebrow">Recent Observations</div>
          <h2 className="panel-title">What changed lately?</h2>
        </div>
      </div>
      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>Time</th>
              <th>AQI</th>
              <th>Category</th>
              <th>PM2.5</th>
              <th>PM10</th>
              <th>Risk</th>
            </tr>
          </thead>
          <tbody>
            {preview.map((row) => (
              <tr key={`${row.geo_id}-${row.ts}`}>
                <td>{formatTimestamp(row.ts)}</td>
                <td>{formatMetricValue(row.aqi, "aqi")}</td>
                <td>
                  <span
                    className="aqi-badge aqi-badge--inline"
                    style={{
                      backgroundColor: aqiTheme(row.aqi_category).soft,
                      color: aqiTheme(row.aqi_category).color,
                    }}
                  >
                    {row.aqi_category}
                  </span>
                </td>
                <td>{formatMetricValue(row.pm2_5, "pm2_5")}</td>
                <td>{formatMetricValue(row.pm10, "pm10")}</td>
                <td>{formatMetricValue(row.risk_score, "risk_score")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
