import { useMemo } from "react";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { METRIC_OPTIONS } from "../shared/constants.js";
import { aqiTheme, sortByMetric } from "../shared/dashboard.js";
import { formatMetricValue, formatTimestamp } from "../shared/formatters.js";

export function ComparePage({ latestByCity, metric, onMetricChange }) {
  const sorted = useMemo(() => sortByMetric(latestByCity, metric), [latestByCity, metric]);

  return (
    <div className="page-stack">
      <section className="panel">
        <div className="panel__header panel__header--split">
          <div>
            <div className="eyebrow">Compare Cities</div>
            <h2 className="panel-title">Latest rankings across the class dashboard</h2>
          </div>
          <select className="select" value={metric} onChange={(event) => onMetricChange(event.target.value)}>
            {METRIC_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
        <div className="chart-wrap">
          <ResponsiveContainer width="100%" height={360}>
            <BarChart layout="vertical" data={sorted} margin={{ left: 20 }}>
              <CartesianGrid strokeDasharray="4 8" horizontal={false} stroke="#DBE4F2" />
              <XAxis type="number" tick={{ fill: "#5D657C", fontSize: 12 }} />
              <YAxis type="category" dataKey="city" tick={{ fill: "#5D657C", fontSize: 12 }} width={90} />
              <Tooltip formatter={(value) => formatMetricValue(Number(value), metric)} />
              <Bar dataKey={metric} radius={[0, 18, 18, 0]}>
                {sorted.map((entry) => (
                  <Cell key={entry.geo_id} fill={aqiTheme(entry.aqi_category).color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section className="panel">
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>City</th>
                <th>Updated</th>
                <th>AQI</th>
                <th>Category</th>
                <th>PM2.5</th>
                <th>PM10</th>
                <th>24h Avg</th>
                <th>Risk</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((row) => (
                <tr key={row.geo_id}>
                  <td>
                    {row.city}, {row.country_code}
                  </td>
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
                  <td>{formatMetricValue(row.pm2_5_24h_avg, "pm2_5")}</td>
                  <td>{formatMetricValue(row.risk_score, "risk_score")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
