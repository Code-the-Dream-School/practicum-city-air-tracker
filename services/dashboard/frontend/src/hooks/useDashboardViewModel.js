import { useMemo } from "react";
import { useDashboardData } from "./useDashboardData.js";
import { useLocalStorageState } from "./useLocalStorageState.js";
import { PAGE_OPTIONS, STORAGE_KEYS } from "../shared/constants.js";

export function useDashboardViewModel() {
  const { payload, loading, error, reload } = useDashboardData();
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

  return {
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
  };
}
