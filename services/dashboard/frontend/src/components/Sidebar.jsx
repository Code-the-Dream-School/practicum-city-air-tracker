import { Database, RefreshCw, Sparkles } from "lucide-react";
import { PAGE_OPTIONS } from "../shared/constants.js";
import { formatTimestamp } from "../shared/formatters.js";

export function Sidebar({ activePage, latestByCity, onCityChange, onPageChange, payload, selectedGeoId }) {
  return (
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
              onClick={() => onPageChange(page.id)}
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
          value={selectedGeoId}
          onChange={(event) => onCityChange(event.target.value)}
        >
          {latestByCity.map((row) => (
            <option key={row.geo_id} value={row.geo_id}>
              {row.city}, {row.country_code}
            </option>
          ))}
        </select>
        <div className="sidebar__tiny">Your last selected city, page, and metric are remembered on this device.</div>
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
  );
}
