import { useEffect, useState } from "react";

// Debounce a changing value so callers don't hit the API on every keypress.
const useDebounced = <T>(value: T, delay: number): T => {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const handle = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(handle);
  }, [value, delay]);
  return debounced;
};

export default useDebounced;
