import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { METRIC_OPTIONS } from "../shared/constants.js";
import { aqiTheme } from "../shared/dashboard.js";
import { formatAxisTimestamp, formatMetricValue, formatTimestamp } from "../shared/formatters.js";

export function TrendPanel({ rows, metric, onMetricChange }) {
  const theme = aqiTheme(rows.at(-1)?.aqi_category);

  return (
    <section className="panel">
      <div className="panel__header panel__header--split">
        <div>
          <div className="eyebrow">Now vs Recent</div>
          <h2 className="panel-title">72h Trend</h2>
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
        <ResponsiveContainer width="100%" height={320}>
          <LineChart data={rows}>
            <CartesianGrid strokeDasharray="4 8" vertical={false} stroke="#DBE4F2" />
            <XAxis dataKey="ts" tickFormatter={formatAxisTimestamp} tick={{ fill: "#5D657C", fontSize: 12 }} />
            <YAxis tick={{ fill: "#5D657C", fontSize: 12 }} />
            <Tooltip
              formatter={(value) => formatMetricValue(Number(value), metric)}
              labelFormatter={formatTimestamp}
              contentStyle={{
                borderRadius: 16,
                border: "1px solid #D9E4F4",
                boxShadow: "0 16px 40px rgba(15, 23, 42, 0.12)",
              }}
            />
            <Line
              type="monotone"
              dataKey={metric}
              stroke={theme.color}
              strokeWidth={4}
              dot={false}
              activeDot={{ r: 6, fill: theme.color }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
