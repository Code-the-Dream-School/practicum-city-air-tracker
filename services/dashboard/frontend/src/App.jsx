import { AlertTriangle, Database, RefreshCw } from "lucide-react";
import { DashboardShell } from "./components/DashboardShell.jsx";
import { EmptyState, ErrorState, LoadingState } from "./components/StateCard.jsx";
import { useDashboardViewModel } from "./hooks/useDashboardViewModel.js";
import { ComparePage } from "./pages/ComparePage.jsx";
import { CityTrendsPage } from "./pages/CityTrendsPage.jsx";
import { OverviewPage } from "./pages/OverviewPage.jsx";

function App() {
  const {
    payload,
    loading,
    error,
    reload,
    activePage,
    setActivePage,
    metric,
    setMetric,
    selectedGeoId,
    setSelectedGeoId,
    selectedCity,
    latestByCity,
    cityRows,
  } = useDashboardViewModel();

  if (loading) {
    return (
      <LoadingState
        icon={RefreshCw}
        title="Loading your happy air widgets..."
        description="We’re gathering the latest student-friendly air stories from PostgreSQL."
      />
    );
  }

  if (error) {
    return (
      <ErrorState
        icon={AlertTriangle}
        title="The dashboard could not load"
        description={error}
        actionLabel="Try Again"
        onAction={reload}
      />
    );
  }

  if (!payload || !latestByCity.length || !selectedCity) {
    return (
      <EmptyState
        icon={Database}
        title="No dashboard data found yet"
        description="Run the pipeline first so PostgreSQL has recent air-quality rows to display."
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
