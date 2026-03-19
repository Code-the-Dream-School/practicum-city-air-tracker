import { AlertTriangle, Database, RefreshCw } from "lucide-react";
import { useMemo } from "react";
import { DashboardShell } from "./components/DashboardShell.jsx";
import { EmptyState, ErrorState, LoadingState } from "./components/StateCard.jsx";
import { useDashboardData } from "./hooks/useDashboardData.js";
import { useLocalStorageState } from "./hooks/useLocalStorageState.js";
import { ComparePage } from "./pages/ComparePage.jsx";
import { CityTrendsPage } from "./pages/CityTrendsPage.jsx";
import { OverviewPage } from "./pages/OverviewPage.jsx";
import { PAGE_OPTIONS, STORAGE_KEYS } from "./shared/constants.js";

function App() {
  const { payload, loading, error } = useDashboardData();
  const [activePage, setActivePage] = useLocalStorageState(STORAGE_KEYS.activePage, PAGE_OPTIONS[0].id);
  const [metric, setMetric] = useLocalStorageState(STORAGE_KEYS.metric, "aqi");
  const [selectedGeoId, setSelectedGeoId] = useLocalStorageState(STORAGE_KEYS.selectedGeoId, "");

  const latestByCity = payload?.latestByCity ?? [];
  const rows = payload?.rows ?? [];

  const selectedCity = useMemo(() => {
    if (!latestByCity.length) {
      return null;
    }

    return latestByCity.find((row) => row.geo_id === selectedGeoId) ?? latestByCity[0];
  }, [latestByCity, selectedGeoId]);

  const cityRows = useMemo(
    () => rows.filter((row) => row.geo_id === selectedCity?.geo_id),
    [rows, selectedCity],
  );

  if (loading) {
    return (
      <LoadingState
        icon={RefreshCw}
        title="Loading your happy air widgets..."
        description="We’re gathering the latest student-friendly air stories from the parquet dataset."
      />
    );
  }

  if (error) {
    return <ErrorState icon={AlertTriangle} title="The dashboard could not load" description={error} />;
  }

  if (!payload || !latestByCity.length || !selectedCity) {
    return (
      <EmptyState
        icon={Database}
        title="No dataset found yet"
        description="Run the pipeline first so the dashboard has a gold parquet file to read."
      />
    );
  }

  return (
    <DashboardShell
      activePage={activePage}
      onPageChange={setActivePage}
      payload={payload}
      selectedCity={selectedCity}
      selectedGeoId={selectedCity.geo_id}
      onCityChange={setSelectedGeoId}
    >
      {activePage === "overview" ? <OverviewPage latestByCity={latestByCity} summary={payload.summary} /> : null}
      {activePage === "city-trends" ? (
        <CityTrendsPage
          cityRows={cityRows}
          latestByCity={latestByCity}
          metric={metric}
          onMetricChange={setMetric}
          selectedCity={selectedCity}
        />
      ) : null}
      {activePage === "compare" ? (
        <ComparePage latestByCity={latestByCity} metric={metric} onMetricChange={setMetric} />
      ) : null}
    </DashboardShell>
  );
}

export default App;
