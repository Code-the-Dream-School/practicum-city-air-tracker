import { useCallback, useEffect, useRef, useState } from "react";

export function useDashboardData() {
  const [payload, setPayload] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const activeControllerRef = useRef(null);

  const loadData = useCallback(async () => {
    activeControllerRef.current?.abort();
    const controller = new AbortController();
    activeControllerRef.current = controller;

    try {
      setLoading(true);
      setError("");

      const response = await fetch("/api/dashboard", { signal: controller.signal });
      if (!response.ok) {
        throw new Error(`Dashboard API returned ${response.status}`);
      }

      const data = await response.json();
      if (!controller.signal.aborted) {
        setPayload(data);
      }
    } catch (loadError) {
      if (loadError instanceof DOMException && loadError.name === "AbortError") {
        return;
      }

      if (!controller.signal.aborted) {
        setError(loadError instanceof Error ? loadError.message : "Unknown dashboard error");
      }
    } finally {
      if (!controller.signal.aborted) {
        setLoading(false);
      }
      if (activeControllerRef.current === controller) {
        activeControllerRef.current = null;
      }
    }
  }, []);

  useEffect(() => {
    loadData();

    return () => {
      activeControllerRef.current?.abort();
    };
  }, [loadData]);

  return { payload, loading, error, reload: loadData };
}
