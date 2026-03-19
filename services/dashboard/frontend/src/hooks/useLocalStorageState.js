import { useEffect, useState } from "react";

function readStoredValue(key, fallbackValue) {
  if (typeof window === "undefined") {
    return fallbackValue;
  }

  return window.localStorage.getItem(key) ?? fallbackValue;
}

export function useLocalStorageState(key, fallbackValue) {
  const [value, setValue] = useState(() => readStoredValue(key, fallbackValue));

  useEffect(() => {
    if (typeof window === "undefined" || value == null || value === "") {
      return;
    }

    window.localStorage.setItem(key, value);
  }, [key, value]);

  return [value, setValue];
}
