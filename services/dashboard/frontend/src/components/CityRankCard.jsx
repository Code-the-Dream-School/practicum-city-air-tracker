import { sortByMetric } from "../shared/dashboard.js";

export function CityRankCard({ latestByCity, selectedCity }) {
  const riskRanking = sortByMetric(latestByCity, "risk_score");
  const pmRanking = sortByMetric(latestByCity, "pm10");
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
