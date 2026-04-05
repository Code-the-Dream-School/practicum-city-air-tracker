import { LatestSnapshot } from "../components/LatestSnapshot.jsx";
import { ObservationsTable } from "../components/ObservationsTable.jsx";
import { TrendPanel } from "../components/TrendPanel.jsx";
import { sortByMetric } from "../shared/dashboard.js";
import { formatMetricValue } from "../shared/formatters.js";

export function CityTrendsPage({ cityRows, latestByCity, metric, onMetricChange, selectedCity }) {
  const ranking = sortByMetric(latestByCity, "risk_score").slice(0, 5);

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
          {ranking.map((row, index) => (
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
