import { useMemo, useSyncExternalStore } from "react";

const KEY = "boomFilterBuilderClipboard";
const listeners = new Set<() => void>();
let copied: string | null = null;

const read = () => {
  try {
    return localStorage.getItem(KEY) ?? copied;
  } catch {
    return copied;
  }
};

const subscribe = (listener: () => void) => {
  listeners.add(listener);
  window.addEventListener("storage", listener);
  return () => {
    listeners.delete(listener);
    window.removeEventListener("storage", listener);
  };
};

const store = (value: string) => {
  try {
    localStorage.setItem(KEY, value);
    return true;
  } catch {
    return false;
  }
};

export const copyFilterItem = (item: any) => {
  copied = JSON.stringify(item);
  store(copied);
  listeners.forEach((listener) => listener());
};

export const useCopiedFilterItem = () => {
  const raw = useSyncExternalStore(subscribe, read);
  return useMemo(() => {
    try {
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  }, [raw]);
};
