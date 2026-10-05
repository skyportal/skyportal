import { useSearchParams } from "react-router-dom";

const useTabParam = (names: string[]) => {
  const [searchParams, setSearchParams] = useSearchParams();
  const tab = Math.max(0, names.indexOf(searchParams.get("tab") ?? ""));
  const setTab = (index: number) =>
    setSearchParams(
      (previous) => {
        const next = new URLSearchParams(previous);
        if (index === 0) next.delete("tab");
        else next.set("tab", names[index] ?? "");
        return next;
      },
      { replace: true },
    );
  return [tab, setTab] as const;
};

export default useTabParam;
