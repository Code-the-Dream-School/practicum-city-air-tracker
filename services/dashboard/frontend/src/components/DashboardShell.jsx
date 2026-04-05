import { Sidebar } from "./Sidebar.jsx";
import { Topbar } from "./Topbar.jsx";

export function DashboardShell({
  activePage,
  children,
  onCityChange,
  onPageChange,
  payload,
  selectedCity,
  selectedGeoId,
}) {
  return (
    <div className="shell">
      <Sidebar
        activePage={activePage}
        latestByCity={payload.latestByCity}
        onCityChange={onCityChange}
        onPageChange={onPageChange}
        payload={payload}
        selectedGeoId={selectedGeoId}
      />

      <main className="content">
        <Topbar latestTimestamp={payload.summary.latestTimestamp} selectedCity={selectedCity} />
        {children}
      </main>
    </div>
  );
}
