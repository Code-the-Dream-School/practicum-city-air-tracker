import { AlertTriangle, Database, Gauge, MapPinned, Sparkles, Wind } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { WidgetCard } from "../components/WidgetCard.jsx";
import { aqiTheme, sortByMetric } from "../shared/dashboard.js";
import { formatMetricValue, formatTimestamp } from "../shared/formatters.js";

export function OverviewPage({ latestByCity, summary }) {
  const highestRisk = summary.highestRiskCity;
  const dirtiest = summary.worstPm25City;
  const ranking = sortByMetric(latestByCity, "risk_score");

  return (
    <div className="page-stack">
      <section className="hero-panel">
        <div className="hero-panel__copy">
          <div className="eyebrow eyebrow--bright">A bright little dashboard for student explorers</div>
          <h1>Track the air story of every city in one cheerful place.</h1>
          <p>
            Start with a current snapshot, then follow the trend lines to see how air quality has shifted across the
            last 72 hours.
          </p>
        </div>
        <div className="hero-panel__widgets">
          <WidgetCard
            icon={MapPinned}
            title="Cities Monitored"
            value={summary.citiesCount}
            detail="Tracked in the latest pipeline run"
            tone="sun"
          />
          <WidgetCard
            icon={Gauge}
            title="Average AQI"
            value={formatMetricValue(summary.averageAqi, "aqi")}
            detail="Across latest city readings"
            tone="mint"
          />
          <WidgetCard
            icon={Sparkles}
            title="Last Refresh"
            value={formatTimestamp(summary.latestTimestamp)}
            detail="Most recent observation in the dataset"
            tone="berry"
          />
        </div>
      </section>

      <div className="widget-grid widget-grid--three">
        <WidgetCard
          icon={AlertTriangle}
          title="Highest Risk City"
          value={highestRisk ? highestRisk.city : "--"}
          detail={highestRisk ? `Risk score ${formatMetricValue(highestRisk.risk_score, "risk_score")}` : "No data"}
          tone="coral"
        />
        <WidgetCard
          icon={Wind}
          title="Highest PM2.5"
          value={dirtiest ? dirtiest.city : "--"}
          detail={dirtiest ? `${formatMetricValue(dirtiest.pm2_5, "pm2_5")} ug/m3` : "No data"}
          tone="sky"
        />
        <WidgetCard
          icon={Database}
          title="Rows Loaded"
          value={summary.rowCount}
          detail="PostgreSQL observations available to the dashboard"
          tone="lavender"
        />
      </div>

      <section className="panel">
        <div className="panel__header">
          <div>
            <div className="eyebrow">Compare Snapshot</div>
            <h2 className="panel-title">Latest city ranking by risk score</h2>
          </div>
        </div>
        <div className="chart-wrap">
          <ResponsiveContainer width="100%" height={340}>
            <BarChart data={ranking}>
              <CartesianGrid strokeDasharray="4 8" vertical={false} stroke="#DBE4F2" />
              <XAxis dataKey="city" tick={{ fill: "#5D657C", fontSize: 12 }} />
              <YAxis tick={{ fill: "#5D657C", fontSize: 12 }} />
              <Tooltip formatter={(value) => formatMetricValue(Number(value), "risk_score")} />
              <Bar dataKey="risk_score" radius={[18, 18, 0, 0]}>
                {ranking.map((entry) => (
                  <Cell key={entry.geo_id} fill={aqiTheme(entry.aqi_category).color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>
    </div>
  );
}
