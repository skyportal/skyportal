import { useEffect, useState } from "react";

/**
 * Delay propagating a rapidly-changing value (typically a search input) until
 * it has been stable for `delay` ms, so callers do not fire a request per
 * keystroke.
 */
export const useDebouncedValue = <T>(value: T, delay = 500): T => {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const handle = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(handle);
  }, [value, delay]);

  return debounced;
};

export default useDebouncedValue;
