import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  BarChart3,
  CloudSun,
  Database,
  Gauge,
  Home,
  MapPinned,
  RefreshCw,
  Sparkles,
  TrendingUp,
  Wind,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const PAGE_OPTIONS = [
  { id: "overview", label: "Overview", icon: Home },
  { id: "city-trends", label: "City Trends", icon: TrendingUp },
  { id: "compare", label: "Compare Cities", icon: BarChart3 },
];

const METRIC_OPTIONS = [
  { value: "aqi", label: "AQI" },
  { value: "pm2_5", label: "PM2.5" },
  { value: "pm10", label: "PM10" },
  { value: "risk_score", label: "Risk Score" },
];

const AQI_THEME = {
  Good: { color: "#2FA66A", soft: "#E6F8EE" },
  Fair: { color: "#7DBA3C", soft: "#F0F8DF" },
  Moderate: { color: "#F5B83D", soft: "#FFF5DC" },
  Poor: { color: "#F47A42", soft: "#FFE8DD" },
  "Very Poor": { color: "#E4504D", soft: "#FFE3E4" },
  Unknown: { color: "#7A839A", soft: "#EEF1F7" },
};

function formatMetricValue(value, metric) {
  if (value == null || Number.isNaN(value)) {
    return "--";
  }

  if (metric === "aqi") {
    return `${Math.round(value)}`;
  }

  if (metric === "risk_score") {
    return `${value.toFixed(1)}`;
  }

  return `${value.toFixed(1)}`;
}

function formatTimestamp(value) {
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

function formatAxisTimestamp(value) {
  const date = new Date(value);
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
  }).format(date);
}

function aqiTheme(category) {
  return AQI_THEME[category] ?? AQI_THEME.Unknown;
}

function WidgetCard({ icon: Icon, title, value, detail, tone = "sky", children }) {
  return (
    <section className={`widget-card widget-card--${tone}`}>
      <div className="widget-card__header">
        <span className="widget-card__icon">
          <Icon size={18} />
        </span>
        <span className="widget-card__title">{title}</span>
      </div>
      <div className="widget-card__value">{value}</div>
      {detail ? <div className="widget-card__detail">{detail}</div> : null}
      {children}
    </section>
  );
}

function StatPill({ label, value, icon: Icon }) {
  return (
    <div className="stat-pill">
      <span className="stat-pill__icon">
        <Icon size={16} />
      </span>
      <div>
        <div className="stat-pill__label">{label}</div>
        <div className="stat-pill__value">{value}</div>
      </div>
    </div>
  );
}

function CityRankCard({ latestByCity, selectedCity }) {
  const riskRanking = [...latestByCity].sort((a, b) => (b.risk_score ?? 0) - (a.risk_score ?? 0));
  const pmRanking = [...latestByCity].sort((a, b) => (b.pm10 ?? 0) - (a.pm10 ?? 0));
  const riskIndex = riskRanking.findIndex((row) => row.geo_id === selectedCity.geo_id) + 1;
  const pmIndex = pmRanking.findIndex((row) => row.geo_id === selectedCity.geo_id) + 1;

  return (
    <div className="mini-card">
      <div className="mini-card__title">Rank Among Cities</div>
      <div className="mini-card__line">#{riskIndex} by risk score</div>
      <div className="mini-card__line">#{pmIndex} by PM10</div>
    </div>
  );
}

function LatestSnapshot({ city, latestByCity, latestTimestamp }) {
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

      <div className="snapshot__footer">Updated {formatTimestamp(city.ts)} · Dataset refreshed {formatTimestamp(latestTimestamp)}</div>
      <CityRankCard latestByCity={latestByCity} selectedCity={city} />
    </section>
  );
}

function TrendPanel({ rows, metric, onMetricChange }) {
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

function ObservationsTable({ rows }) {
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

function OverviewPage({ latestByCity, summary }) {
  const highestRisk = summary.highestRiskCity;
  const dirtiest = summary.worstPm25City;

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
          detail="Parquet observations available to the dashboard"
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
            <BarChart data={[...latestByCity].sort((a, b) => (b.risk_score ?? 0) - (a.risk_score ?? 0))}>
              <CartesianGrid strokeDasharray="4 8" vertical={false} stroke="#DBE4F2" />
              <XAxis dataKey="city" tick={{ fill: "#5D657C", fontSize: 12 }} />
              <YAxis tick={{ fill: "#5D657C", fontSize: 12 }} />
              <Tooltip formatter={(value) => formatMetricValue(Number(value), "risk_score")} />
              <Bar dataKey="risk_score" radius={[18, 18, 0, 0]}>
                {latestByCity.map((entry) => (
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

function CityTrendsPage({ cityRows, selectedCity, latestByCity, metric, onMetricChange }) {
  return (
    <div className="split-layout">
      <LatestSnapshot city={selectedCity} latestByCity={latestByCity} latestTimestamp={cityRows.at(-1)?.ts} />
      <TrendPanel rows={cityRows} metric={metric} onMetricChange={onMetricChange} />
      <ObservationsTable rows={cityRows} />
      <section className="panel">
        <div className="panel__header">
          <div>
            <div className="eyebrow">Quick Compare</div>
            <h2 className="panel-title">How this city stacks up right now</h2>
          </div>
        </div>
        <div className="mini-rankings">
          {[...latestByCity]
            .sort((a, b) => (b.risk_score ?? 0) - (a.risk_score ?? 0))
            .slice(0, 5)
            .map((row, index) => (
              <div className="mini-ranking" key={row.geo_id}>
                <div className="mini-ranking__left">
                  <span className="mini-ranking__rank">{index + 1}</span>
                  <span className="mini-ranking__city">
                    {row.city}, {row.country_code}
                  </span>
                </div>
                <span className="mini-ranking__value">{formatMetricValue(row.risk_score, "risk_score")}</span>
              </div>
            ))}
        </div>
      </section>
    </div>
  );
}

function ComparePage({ latestByCity, metric, onMetricChange }) {
  const sorted = useMemo(
    () => [...latestByCity].sort((a, b) => (b[metric] ?? 0) - (a[metric] ?? 0)),
    [latestByCity, metric],
  );

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

function App() {
  const [payload, setPayload] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activePage, setActivePage] = useState("overview");
  const [metric, setMetric] = useState("aqi");
  const [selectedGeoId, setSelectedGeoId] = useState(() => window.localStorage.getItem("city-air-selected-geo") ?? "");

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        setError("");
        const response = await fetch("/api/dashboard");
        if (!response.ok) {
          throw new Error(`Dashboard API returned ${response.status}`);
        }
        const data = await response.json();
        setPayload(data);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Unknown dashboard error");
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, []);

  useEffect(() => {
    if (selectedGeoId) {
      window.localStorage.setItem("city-air-selected-geo", selectedGeoId);
    }
  }, [selectedGeoId]);

  const latestByCity = payload?.latestByCity ?? [];
  const rows = payload?.rows ?? [];
  const selectedCity = useMemo(() => {
    if (!latestByCity.length) {
      return null;
    }
    return latestByCity.find((row) => row.geo_id === selectedGeoId) ?? latestByCity[0];
  }, [latestByCity, selectedGeoId]);

  useEffect(() => {
    if (!selectedGeoId && latestByCity.length) {
      setSelectedGeoId(latestByCity[0].geo_id);
    }
  }, [latestByCity, selectedGeoId]);

  const cityRows = useMemo(
    () => rows.filter((row) => row.geo_id === selectedCity?.geo_id),
    [rows, selectedCity],
  );

  if (loading) {
    return (
      <div className="shell shell--centered">
        <div className="state-card">
          <RefreshCw className="spin" size={28} />
          <h1>Loading your happy air widgets...</h1>
          <p>We’re gathering the latest student-friendly air stories from the parquet dataset.</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="shell shell--centered">
        <div className="state-card state-card--error">
          <AlertTriangle size={28} />
          <h1>The dashboard could not load</h1>
          <p>{error}</p>
        </div>
      </div>
    );
  }

  if (!payload || !latestByCity.length || !selectedCity) {
    return (
      <div className="shell shell--centered">
        <div className="state-card">
          <Database size={28} />
          <h1>No dataset found yet</h1>
          <p>Run the pipeline first so the dashboard has a gold parquet file to read.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand__badge">
            <Sparkles size={20} />
          </div>
          <div>
            <div className="brand__title">City Air Tracker</div>
            <div className="brand__subtitle">Happy widgets for student explorers</div>
          </div>
        </div>

        <nav className="nav">
          {PAGE_OPTIONS.map((page) => {
            const Icon = page.icon;
            return (
              <button
                key={page.id}
                type="button"
                className={`nav__item ${activePage === page.id ? "nav__item--active" : ""}`}
                onClick={() => setActivePage(page.id)}
              >
                <Icon size={18} />
                <span>{page.label}</span>
              </button>
            );
          })}
        </nav>

        <div className="sidebar__card">
          <label className="sidebar__label" htmlFor="city-select">
            Choose a city
          </label>
          <select
            id="city-select"
            className="select select--full"
            value={selectedCity.geo_id}
            onChange={(event) => setSelectedGeoId(event.target.value)}
          >
            {latestByCity.map((row) => (
              <option key={row.geo_id} value={row.geo_id}>
                {row.city}, {row.country_code}
              </option>
            ))}
          </select>
          <div className="sidebar__tiny">Your last selected city is remembered on this device.</div>
        </div>

        <div className="sidebar__card sidebar__card--status">
          <div className="sidebar__label">Data status</div>
          <div className="status-line">
            <RefreshCw size={14} />
            <span>Freshness: {formatTimestamp(payload.summary.latestTimestamp)}</span>
          </div>
          <div className="status-line">
            <Database size={14} />
            <span>{payload.summary.rowCount} observations ready</span>
          </div>
        </div>
      </aside>

      <main className="content">
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
            <span className="topbar__timestamp">Latest data: {formatTimestamp(payload.summary.latestTimestamp)}</span>
          </div>
        </header>

        {activePage === "overview" ? <OverviewPage latestByCity={latestByCity} summary={payload.summary} /> : null}
        {activePage === "city-trends" ? (
          <CityTrendsPage
            cityRows={cityRows}
            selectedCity={selectedCity}
            latestByCity={latestByCity}
            metric={metric}
            onMetricChange={setMetric}
          />
        ) : null}
        {activePage === "compare" ? <ComparePage latestByCity={latestByCity} metric={metric} onMetricChange={setMetric} /> : null}
      </main>
    </div>
  );
}

export default App;
